import {test} from "node:test";
import assert from "node:assert/strict";
import {handleAcknowledgment} from "./gmail-acknowledgment-transport.mjs";

const original = "To: synthetic@example.invalid\r\nX-ELH-Receipt: AB1234CD5678\r\nMIME-Version: 1.0\r\n\r\nApproved letter";
const request = {action:"send_acknowledgment",raw:Buffer.from(original).toString("base64url")};
function fake({mailbox="synthetic@eternallifehospice.com",connections=[{status:"healthy"}],
               sendStatus=200,result={id:"synthetic-gmail"},networkFailure=false,
               profileStatus=200}={}) {
  const calls = [];
  return {calls,
    async listConnections() { return connections; },
    async proxy(name,path,options) {
      assert.equal(name,"google-mail");
      calls.push({path,options});
      if (path.endsWith("/profile"))
        return new Response(JSON.stringify({emailAddress:mailbox}),{status:profileStatus});
      assert.equal(path,"/gmail/v1/users/me/messages/send");
      if (networkFailure) throw new Error("Synthetic lost response");
      return new Response(JSON.stringify(result),{status:sendStatus});
    }
  };
}

test("profile check never sends email",async()=>{
  const transport = fake();
  const result = await handleAcknowledgment({action:"profile"},transport);
  assert.equal(result.sender,"synthetic@eternallifehospice.com");
  assert.equal(transport.calls.length,1);
  assert.equal(transport.calls[0].options.method,"GET");
});

test("one send, verified company sender, original MIME preserved",async()=>{
  const transport = fake();
  assert.deepEqual(await handleAcknowledgment(request,transport),
    {ok:true,message_id:"synthetic-gmail"});
  const posts = transport.calls.filter(call=>call.options.method==="POST");
  assert.equal(posts.length,1);
  const sent = JSON.parse(posts[0].options.body);
  assert.equal(Buffer.from(sent.raw,"base64url").toString(),
    "From: Eternal Life Hospice <synthetic@eternallifehospice.com>\r\n"+original);
});

test("personal, absent, unhealthy and ambiguous mailboxes fail closed",async()=>{
  for (const setup of [{mailbox:"synthetic@gmail.com"},{connections:[]},
    {connections:[{status:"unhealthy"}]},
    {connections:[{status:"healthy"},{status:"healthy"}]},
    {profileStatus:403}]) {
    const transport = fake(setup);
    await assert.rejects(handleAcknowledgment(request,transport));
    assert.equal(transport.calls.filter(call=>call.options.method==="POST").length,0);
  }
});

test("unknown delivery, rejection and missing provider ID are not retried",async()=>{
  for (const setup of [{networkFailure:true},{sendStatus:503},{sendStatus:403},{result:{}}]) {
    const transport = fake(setup);
    await assert.rejects(handleAcknowledgment(request,transport));
    assert.equal(transport.calls.filter(call=>call.options.method==="POST").length,1);
  }
});

test("no arbitrary action, sender override or additional recipients",async()=>{
  for (const input of [{action:"arbitrary"}, {...request,raw:"bad!"},
    ...["From: attacker@example.invalid\r\n","Cc: other@example.invalid\r\n",
        "Bcc: other@example.invalid\r\n","Sender: attacker@example.invalid\r\n"]
      .map(header=>({...request,raw:Buffer.from(header+original).toString("base64url")}))]) {
    const transport = fake();
    await assert.rejects(handleAcknowledgment(input,transport));
    assert.equal(transport.calls.length,0);
  }
});
