# Aditi's Presentation Script

## Your Part: Demo — Product Comparison + Advisory Agent

---

## DEMO: Product Comparison (after Gunjan's RAG demo) — 1 minute

### In the app (http://localhost:8501)

**Say:**

> "Now let me show you the product advisory capability.
>
> [Reset chat if needed]
> [Type in chat: 'Compare HP Pavilion and Lenovo IdeaPad for college use']
> [Wait for response]
>
> The system understands this is a product inquiry and routes it to MY agent — the Product Advisory Agent.
>
> [Point to the response]
>
> See — it gives a comparison with specific details: specs, pricing, what each is best for, and a recommendation based on the use case 'college'.
>
> [Expand Agent Console if visible]
>
> My agent loads a catalog of 92 products — laptops, phones, headphones, fashion, home appliances. It:
> 1. Identifies the products mentioned in the message
> 2. Pulls their full specs from the catalog
> 3. Compares them side-by-side
> 4. Recommends based on the stated use case
> 5. Suggests alternatives if something is out of stock
>
> This handles the pre-purchase support problem — customers who need help choosing. In the old system, this would require a specialized sales agent. Now it's automated.
>
> I also improved the intent classifier — I built a priority-ordered keyword system that correctly distinguishes between 'my product is damaged' (support) vs 'tell me about this product' (advisory). The order matters — damage keywords are checked before product keywords.
>
> Rohan, show them what happens when things go wrong."

**[Hand over to Rohan]**

---

## Your Code Files (if asked)

```
src/agents/product_advisory.py — Your agent:
  - Loads from src/knowledge/products/catalog.json (92 products)
  - Parses product names from customer message
  - Compares specs side-by-side
  - Recommends based on use case
  - Suggests alternatives for out-of-stock

src/knowledge/products/catalog.json — Product data:
  - 92 products across categories
  - Full specs: processor, RAM, storage, battery, display, weight, rating
  - Stock status, warranty, price
  - 'best_for' field for recommendations

src/agents/intent_classifier.py — Your improvements:
  - MOCK_KEYWORD_GROUPS: priority-ordered matching
  - 'damaged_product' checked BEFORE 'product_inquiry'
  - Sentiment override words (_ANGRY_WORDS, _FRUSTRATED_WORDS)
```
