# Gunjan's Presentation Script

## Your Part: Demo — Policy Retrieval + RAG Explanation

---

## DEMO: Policy Query with RAG (after Pallavi's order tracking demo) — 1.5 minutes

### In the app (http://localhost:8501)

**Say:**

> "Now let me show you our knowledge layer — this is what makes our system trustworthy.
>
> [Type in chat: 'I want my money back, when will I get my refund?']
> [Wait for response]
>
> See — the system found the refund policy and gave a specific answer with timelines. But HOW did it find the right policy? Let me show you.
>
> [Expand Agent Console -> 'Policy (RAG Embeddings)' toggle]
>
> See these policy snippets? Each one has a reference ID like POL-REF-TIME-001 and a similarity score.
>
> This is NOT keyword matching. This is RAG — Retrieval Augmented Generation — with vector embeddings.
>
> Here's how it works:
> 1. I created 23 policy rules across 7 categories — returns, refunds, warranty, delivery, coupons, seller rules, and general FAQ
> 2. At startup, ALL 23 policies are embedded into vectors using OpenAI's text-embedding-3-small model
> 3. When the customer says 'I want my money back', that query is ALSO embedded into a vector
> 4. We calculate cosine similarity between the query vector and all 23 policy vectors
> 5. Top 3 matches are returned
>
> The magic: 'I want my money back' has ZERO keyword overlap with 'Refunds are processed within 5-7 business days'. But semantically, they mean the same thing. The embeddings capture that meaning.
>
> This is why our system never gives wrong policy information — it only cites what's actually in our verified knowledge base. No hallucination possible.
>
> [Point to reference IDs]
>
> Every response cites these reference IDs. An auditor can trace exactly which policy was used for which answer."

**[Hand over to Aditi]**

---

## Your Code Files (if asked)

```
src/knowledge/embedding_store.py — The RAG engine:
  - PolicyEmbeddingStore class
  - load_policies(): loads 23 rules, embeds them
  - search(): embeds query, cosine similarity, returns top 3

src/knowledge/policies/ — Your 7 policy JSON files:
  - return_policy.json (4 rules: electronics 7 days, fashion 15 days, groceries, home)
  - refund_policy.json (3 rules: timeline, payment method, partial)
  - warranty_policy.json (warranty coverage rules)
  - delivery_policy.json (delay compensation, lost shipment)
  - coupon_policy.json (eligibility, stacking, expiry)
  - seller_policy.json (seller vs ShopEase fulfilled)
  - general_faq.json (cancellation, general)

src/knowledge/faqs/faq_database.json — 20 FAQ entries
src/knowledge/products/catalog.json — 92 products (contributed by you + Rohan)

src/agents/policy_retrieval.py — Your agent:
  - Uses embeddings in LIVE mode
  - Falls back to keyword scoring in MOCK mode
  - Returns policy_snippets with reference_ids and confidence
```

---

## Key Point to Emphasize

> "The response generator can ONLY use policies we provide. It cannot make things up. If no policy matches above 0.3 similarity, it says 'I dont have enough information' — that's safer than guessing."
