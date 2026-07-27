/* Eternal Life Hospice — Google Reviews proxy (Netlify Function).
 *
 * Calls the Places API (New) and returns the aggregate rating + up to 5
 * reviews. Responses are cached for 1 hour via Cache-Control so the API
 * quota stays minimal. The API key (GOOGLE_API_KEY) lives only in Netlify
 * environment variables and is never exposed to the browser.
 */

const PLACE_ID = "ChIJteBBU6vdfEcRqUfOqdzxmoc";

exports.handler = async function (event) {
  // Only allow GET
  if (event.httpMethod !== "GET") {
    return respond(405, { error: "Method not allowed" });
  }

  const KEY = process.env.GOOGLE_API_KEY;
  if (!KEY) {
    return respond(500, { error: "Reviews API not configured" });
  }

  try {
    const apiResp = await fetch(
      `https://places.googleapis.com/v1/places/${PLACE_ID}`,
      {
        headers: {
          "X-Goog-Api-Key": KEY,
          "X-Goog-FieldMask": "id,rating,userRatingCount,reviews"
        }
      }
    );

    if (!apiResp.ok) {
      const detail = await apiResp.text();
      console.error("Places API error", apiResp.status, detail.slice(0, 200));
      return respond(502, { error: "Places API returned " + apiResp.status });
    }

    const data = await apiResp.json();

    const reviews = (data.reviews || []).map(function (r) {
      return {
        author: (r.authorAttribution && r.authorAttribution.displayName) || "Anonymous",
        rating: r.rating || 5,
        text: (r.text && r.text.text) || "",
        relative: r.relativePublishTimeDescription || ""
      };
    });

    return {
      statusCode: 200,
      headers: {
        "Content-Type": "application/json",
        // Cache at the CDN edge for 1 hour, allow stale for 10 min while revalidating
        "Cache-Control": "public, max-age=3600, stale-while-revalidate=600"
      },
      body: JSON.stringify({
        rating: data.rating || 5,
        total: data.userRatingCount || 0,
        reviews: reviews
      })
    };
  } catch (err) {
    console.error("reviews.js error:", err && err.message);
    return respond(502, { error: "Upstream error" });
  }
};

function respond(statusCode, obj) {
  return {
    statusCode: statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(obj)
  };
}
