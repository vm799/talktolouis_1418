import { NextRequest, NextResponse } from "next/server";
import { MongoClient } from "mongodb";

export async function GET(req: NextRequest) {
  const userId = req.nextUrl.searchParams.get("user_id");
  if (!userId) return NextResponse.json({ events: [] });

  if (!process.env.MONGODB_URI) {
    return NextResponse.json(
      { error: "MONGODB_URI not configured" },
      { status: 500 }
    );
  }

  const client = new MongoClient(process.env.MONGODB_URI);
  try {
    await client.connect();
    const db = client.db();

    // Get events from last 4 hours
    const cutoff = new Date(Date.now() - 4 * 60 * 60 * 1000);
    const events = await db
      .collection("louis_audit_log")
      .find({ user_id: userId, timestamp: { $gte: cutoff } })
      .sort({ timestamp: 1 })
      .limit(100)
      .toArray();

    return NextResponse.json({
      events: events.map((e) => ({
        event_type: e.event_type,
        timestamp: e.timestamp,
        red_flag_status: e.red_flag_status,
        escalation_status: e.escalation_status,
      })),
    });
  } catch (error) {
    console.error("Failed to fetch events:", error);
    return NextResponse.json(
      { error: "Failed to fetch events" },
      { status: 500 }
    );
  } finally {
    await client.close();
  }
}
