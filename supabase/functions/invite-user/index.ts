import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": Deno.env.get("FRONTEND_URL") ?? "",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};

function respond(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders });
}

Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (request.method !== "POST") {
    return respond(405, { error: "Method not allowed." });
  }

  const authorization = request.headers.get("Authorization");
  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const frontendUrl = Deno.env.get("FRONTEND_URL");
  if (!authorization || !supabaseUrl || !anonKey || !serviceRoleKey || !frontendUrl) {
    return respond(500, { error: "Function configuration is incomplete." });
  }

  const callerClient = createClient(supabaseUrl, anonKey, {
    global: { headers: { Authorization: authorization } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: callerData, error: callerError } = await callerClient.auth.getUser();
  if (callerError || !callerData.user) {
    return respond(401, { error: "A valid signed-in user is required." });
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return respond(400, { error: "Request body must be valid JSON." });
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return respond(400, { error: "Request body must be an object." });
  }

  const { email, full_name, role } = payload as Record<string, unknown>;
  if (
    typeof email !== "string" ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) ||
    typeof full_name !== "string" ||
    !full_name.trim() ||
    full_name.trim().length > 200 ||
    !["student", "lecturer", "advisor"].includes(String(role))
  ) {
    return respond(422, { error: "Provide a valid email, name, and student/lecturer/advisor role." });
  }

  const adminClient = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: callerProfile, error: profileError } = await adminClient
    .from("profiles")
    .select("role")
    .eq("id", callerData.user.id)
    .maybeSingle();
  if (profileError) {
    return respond(500, { error: "Could not verify administrator permissions." });
  }
  if (callerProfile?.role !== "admin") {
    return respond(403, { error: "Administrator access is required to invite accounts." });
  }

  const normalizedEmail = email.trim().toLowerCase();
  const { data: inviteData, error: inviteError } = await adminClient.auth.admin.inviteUserByEmail(
    normalizedEmail,
    { data: { full_name: full_name.trim() }, redirectTo: `${frontendUrl}/login` },
  );
  if (inviteError || !inviteData.user) {
    return respond(400, { error: inviteError?.message ?? "Supabase did not return an invited user." });
  }

  const { error: roleError } = await adminClient
    .from("profiles")
    .update({ full_name: full_name.trim(), role })
    .eq("id", inviteData.user.id);
  if (roleError) {
    return respond(500, {
      error: "The account was invited, but assigning its app role failed. Contact an administrator.",
    });
  }

  return respond(201, { user_id: inviteData.user.id, email: normalizedEmail, role });
});
