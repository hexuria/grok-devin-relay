# Copy/paste to Grok

Please review this draft for `hexuria/grok-devin-relay`. We want one repository
with a shared contract and separate Devin/Grok adapters, not two diverging
protocols. Do not create or change live webhooks during this review.

The draft's lifecycle is:

1. Install only the current provider's adapter.
2. Bootstrap a Devin control-plane webhook.
3. Bootstrap the Grok return relay through supported host tools.
4. Connect a bot to an existing session, a new persistent session, or a
   new-session-per-task webhook.
5. Relay tasks/results and correlated permission questions.

Important: a session link inside a POST to an existing Devin automation does
not change that automation's configured target. Dedicated webhooks have fixed
destinations. Arbitrary per-message routing needs a Grok router/registry or
Devin's documented v3 session API.

Please answer:

- What runtime actually hosts you, and what is its supported skill installer?
- What documented tools/APIs can create your return webhook and authenticate it?
- How do you securely store/exchange credentials? Can you use opaque registry
  aliases such as `adapter:grok:pua-review-inbox-secret`, mapped privately to your
  own secret store? These aliases are proposed, not an existing host feature.
- Where can we persist bot routing, atomic deduplication, and pending questions?
- Can you support the shared version-1 schemas, with response modes `none`,
  `final`, and `progress`, and answers routed to the original question/session?
- How will you authenticate the owner before sending an approve/deny answer?
- For new-per-task bots, how will an answer reach the original task session
  without posting to the webhook that creates a different session? Can you use
  the documented v3 message API or a separately approved fixed-session inbox?

Review `providers/grok/SKILL.md`, `shared/protocol.md`, schemas, and examples.
Suggest changes or a PR against the shared repository; explain any host
capability that is missing rather than inventing an API.

Permission timeouts always remain paused. A chat "approve" does not approve a
Devin platform approval card.

Reply with documentation links and redacted examples only. Never include real
API keys, webhook secrets, or secret-bearing endpoint URLs.
