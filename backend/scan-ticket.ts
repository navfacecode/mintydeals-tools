// ============================================================
// Supabase Edge Function: scan-ticket
// File location: supabase/functions/scan-ticket/index.ts
// Deploy: supabase functions deploy scan-ticket
// ============================================================
//
// SETUP:
// 1. Create a Supabase project at supabase.com
// 2. Install Supabase CLI: npm install -g supabase
// 3. Login: supabase login
// 4. Link project: supabase link --project-ref YOUR_PROJECT_REF
// 5. Set Gemini API key as secret:
//    supabase secrets set GEMINI_API_KEY=your_gemini_key_here
// 6. Deploy this function:
//    supabase functions deploy scan-ticket --no-verify-jwt
// 7. Copy your project URL and anon key into index.html
//
// Get Gemini API key (free tier): https://aistudio.google.com/apikey
// ============================================================

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// ============================================================
// Lottery-specific prompts for Gemini Vision
// ============================================================
const PROMPTS = {
  powerball: `You are analysing a US Powerball lottery ticket image.

Extract ALL plays on this ticket. Each play has:
- 5 main "white ball" numbers (each between 1-69)
- 1 "Powerball" red number (between 1-26)

A ticket may have plays labelled A, B, C, D, E (or 1-5). Extract EVERY play visible.

Also detect if "Power Play" is enabled (yes/no).

Return ONLY valid JSON in this exact format with no markdown, no explanation:
{
  "numbers": [
    {"main": [n1, n2, n3, n4, n5], "bonus": n6, "play": "A"},
    {"main": [n1, n2, n3, n4, n5], "bonus": n6, "play": "B"}
  ],
  "powerPlay": false,
  "ticketDate": "YYYY-MM-DD or null if not visible",
  "confidence": "high|medium|low"
}

If you cannot read the ticket clearly, return: {"error": "unreadable", "reason": "explanation"}`,

  megamillions: `You are analysing a US Mega Millions lottery ticket image.

Extract ALL plays on this ticket. Each play has:
- 5 main "white ball" numbers (each between 1-70)
- 1 "Mega Ball" gold number (between 1-25)

A ticket may have plays labelled A, B, C, D, E (or 1-5). Extract EVERY play visible.

Also detect if "Megaplier" is enabled (yes/no).

Return ONLY valid JSON in this exact format with no markdown, no explanation:
{
  "numbers": [
    {"main": [n1, n2, n3, n4, n5], "bonus": n6, "play": "A"},
    {"main": [n1, n2, n3, n4, n5], "bonus": n6, "play": "B"}
  ],
  "megaplier": false,
  "ticketDate": "YYYY-MM-DD or null if not visible",
  "confidence": "high|medium|low"
}

If you cannot read the ticket clearly, return: {"error": "unreadable", "reason": "explanation"}`,

  kerala: `You are analysing a Kerala State Lottery ticket from India.

Kerala lottery tickets have:
- A ticket series code like "KX 547893" or "KA 123456" (2 letters + 6 digits)
- The lottery name (e.g., Karunya, Win-Win, Nirmal, Akshaya, Karunya Plus, Sthree Sakthi, Pournami)
- A draw number like "KR-756"
- A draw date

Return ONLY valid JSON in this exact format with no markdown:
{
  "ticketSeries": "XX NNNNNN format with space",
  "lotteryName": "e.g., Karunya",
  "drawNumber": "e.g., KR-756 or null",
  "drawDate": "YYYY-MM-DD or null",
  "agentNumber": "agent code if visible or null",
  "confidence": "high|medium|low"
}

If unreadable: {"error": "unreadable", "reason": "explanation"}`,

  nagaland: `You are analysing a Nagaland State Lottery (Dear Lottery) ticket from India.

Nagaland Dear Lottery tickets have:
- A ticket number format like "47K 12345" or "85A 67890" (2 digits + 1 letter + 5 digits)
- Lottery name (Dear Morning, Dear Day, Dear Evening, Dear Night)
- Draw date and time
- A ticket price (₹6 typically)

Return ONLY valid JSON in this exact format with no markdown:
{
  "ticketSeries": "NNL NNNNN format with space",
  "lotteryName": "e.g., Dear Evening",
  "drawDate": "YYYY-MM-DD or null",
  "drawTime": "morning/day/evening/night",
  "confidence": "high|medium|low"
}

If unreadable: {"error": "unreadable", "reason": "explanation"}`,
};

// ============================================================
// Main handler
// ============================================================
serve(async (req) => {
  // CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { image, lottery } = await req.json();

    // Validation
    if (!image) {
      return jsonResponse({ error: "Missing image data" }, 400);
    }
    if (!lottery || !PROMPTS[lottery]) {
      return jsonResponse({ error: "Invalid lottery type" }, 400);
    }

    // Get Gemini API key from secrets
    const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY");
    if (!GEMINI_API_KEY) {
      return jsonResponse({ error: "Server not configured" }, 500);
    }

    // ============================================================
    // Call Gemini Flash 2.0 (cheapest vision-capable model)
    // Cost: ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens
    // Image ~ 258 tokens. Total per scan: ~$0.0001 (₹0.008)
    // ============================================================
    const geminiResponse = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{
            parts: [
              { text: PROMPTS[lottery] },
              {
                inline_data: {
                  mime_type: "image/jpeg",
                  data: image
                }
              }
            ]
          }],
          generationConfig: {
            temperature: 0.1, // Low temp for accurate extraction
            maxOutputTokens: 1024,
            responseMimeType: "application/json"
          }
        })
      }
    );

    if (!geminiResponse.ok) {
      const errorText = await geminiResponse.text();
      console.error("Gemini API error:", errorText);
      return jsonResponse(
        { error: "AI vision service error", details: errorText },
        502
      );
    }

    const geminiData = await geminiResponse.json();
    const rawText = geminiData?.candidates?.[0]?.content?.parts?.[0]?.text;

    if (!rawText) {
      return jsonResponse({ error: "No response from AI" }, 502);
    }

    // Parse the JSON response from Gemini
    let parsed;
    try {
      // Strip any markdown fencing if present
      const cleaned = rawText.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
      parsed = JSON.parse(cleaned);
    } catch (e) {
      console.error("Failed to parse Gemini response:", rawText);
      return jsonResponse(
        { error: "Could not parse ticket data", raw: rawText },
        502
      );
    }

    // Handle unreadable tickets
    if (parsed.error) {
      return jsonResponse(parsed, 200);
    }

    // ============================================================
    // Validation per lottery type
    // ============================================================
    if (lottery === "powerball" || lottery === "megamillions") {
      if (!parsed.numbers || !Array.isArray(parsed.numbers) || parsed.numbers.length === 0) {
        return jsonResponse({
          error: "unreadable",
          reason: "No play data extracted. Try a clearer photo with all numbers visible."
        });
      }

      // Validate number ranges
      const mainMax = lottery === "powerball" ? 69 : 70;
      const bonusMax = lottery === "powerball" ? 26 : 25;

      const validPlays = parsed.numbers.filter(play => {
        if (!play.main || play.main.length !== 5) return false;
        if (!play.main.every(n => Number.isInteger(n) && n >= 1 && n <= mainMax)) return false;
        if (!Number.isInteger(play.bonus) || play.bonus < 1 || play.bonus > bonusMax) return false;
        return true;
      });

      if (validPlays.length === 0) {
        return jsonResponse({
          error: "unreadable",
          reason: "Numbers outside valid range. Please re-scan."
        });
      }

      parsed.numbers = validPlays;
    }

    if (lottery === "kerala" || lottery === "nagaland") {
      if (!parsed.ticketSeries) {
        return jsonResponse({
          error: "unreadable",
          reason: "Ticket series not detected. Ensure the ticket number is clearly visible."
        });
      }
    }

    // ============================================================
    // Optional: Log scan to database for analytics
    // (Uncomment after creating a 'scans' table in Supabase)
    // ============================================================
    /*
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    await fetch(`${supabaseUrl}/rest/v1/scans`, {
      method: "POST",
      headers: {
        "apikey": supabaseKey,
        "Authorization": `Bearer ${supabaseKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        lottery,
        confidence: parsed.confidence,
        result_summary: JSON.stringify(parsed).substring(0, 500),
        created_at: new Date().toISOString()
      })
    });
    */

    return jsonResponse(parsed);

  } catch (error) {
    console.error("Edge function error:", error);
    return jsonResponse({ error: error.message }, 500);
  }
});

// ============================================================
// Helper
// ============================================================
function jsonResponse(body: object, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}
