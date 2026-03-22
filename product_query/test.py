from openai import OpenAI
import os
import json
import time

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

INPUT_PRODUCT_FILE = "products.json"
OUTPUT_FILE = "product_queries.json"

system_prompt = """
You generate user queries following a 4-stage decision framework.
Return only valid JSON.
"""

# ================= Load products =================

with open(INPUT_PRODUCT_FILE, "r", encoding="utf-8") as f:
    products_data = json.load(f)

products = products_data["products"]

results = []

# ================= Loop through products =================

for product in products:

    name = product["name"]
    intent = product["user_intent"]
    complexity = product["decision_complexity"]
    tech = product["technical_level"]

    print("Generating queries for:", name)

    user_prompt = f"""
    Product: {name}

    Product attributes:
    - User intent: {intent}
    - Decision complexity: {complexity}
    - Technical level: {tech}

    Your task is to generate example user questions for this product
    following the SAME structure, cognitive intent, and abstraction level
    as the VPN examples provided below.

    This prompt is designed to be GENERALIZABLE:
    the VPN questions are used ONLY as a reference template.
    You must be able to replace VPN with ANY other product category
    while keeping the same decision logic and question style.

    ==================================
    DECISION FRAMEWORK OVERVIEW
    ==================================

    There are FOUR stages in the user decision journey.
    Each stage has a distinct focus, and B2B and B2C users
    have different decision priorities within the same stage.

    Stage 1: Awareness — Generic Exploration
    • B2B focus:
      - Problem discovery at the organizational level
      - Feasibility, legitimacy, cost, infrastructure, and scale
    • B2C focus:
      - Personal relevance and necessity
      - Understanding what the product does and whether it is needed
      - Considering consequences of non-use and simpler alternatives

    Stage 2: Consideration — Targeted Selection
    • B2B focus:
      - Comparing solutions based on organizational fit
      - Governance, role management, customization, integration
    • B2C focus:
      - Comparing options based on personal use cases
      - Ease of use, device compatibility, and personal context

    Stage 3: Decision — Evaluation before Purchase or Deployment
    • B2B focus:
      - Making a defensible decision for stakeholders
      - SLAs, compliance, certifications, scalability, vendor reliability
    • B2C focus:
      - Minimizing regret and perceived risk
      - Trustworthiness, reviews, value for money, refund or trial options

    Stage 4: Usage — Post-Adoption Evaluation
    • B2B focus:
      - Optimizing usage at scale
      - Cost reduction, maintenance, upgrades, and long-term value
    • B2C focus:
      - Reducing friction in everyday use
      - Setup, troubleshooting, performance, and easy exit

    ==================================
    REFERENCE TEMPLATE (VPN EXAMPLES)
    ==================================

    Awareness – B2B (Enterprise VPN):
    - To solve the cyber security issue, which device is feasible?
    - What is the difference between deploying an enterprise VPN and deploying a local server?
    - What infrastructure is required to deploy an enterprise VPN?
    - How much does an enterprise VPN solution typically cost?
    - Do we need dedicated hardware or servers?

    Awareness – B2C (Personal VPN):
    - What is a VPN used for?
    - Do I really need a VPN for everyday internet use?
    - What happens if I don’t use a VPN?
    - Are there simpler alternatives to using a VPN?

    Consideration – B2B:
    - Differences between site-to-site VPN and remote-access VPN for enterprises
    - Which enterprise VPN supports role-based access control?
    - Which VPN can be customized for different departments?

    Consideration – B2C:
    - Which VPN is best for beginners?
    - Which VPN is suitable for my use case?

    Decision – B2B:
    - Enterprise VPN vendor service quality and SLAs
    - Security certifications and compliance standards

    Decision – B2C:
    - Which VPN has real reviews?
    - Which VPN offers the best value for money?
    - Which VPN has the best security level?


    Usage – B2B:
    - How can we optimize VPN performance for all employees?
    - How do we reduce operating costs of the enterprise VPN?
    - How do we maintain and upgrade the VPN infrastructure?
    - Can the VPN support company expansion or new locations?

    Usage – B2C:
    - How do I set up the VPN on my phone or laptop?
    - What should I do if the VPN connection fails?
    - How can I improve VPN speed?
    - How do I cancel my VPN subscription or request a refund?

    ==================================
    TASK INSTRUCTIONS
    ==================================

    1. For the given product {name}, generate questions for ALL FOUR stages:
      Awareness, Consideration, Decision, Usage.

    2. For EACH stage, generate:
      - 4 questions for B2B (enterprise users)
      - 4 questions for B2C (personal users)

      → Total output MUST be exactly:
        4 stages × 2 user types × 4 questions = 32 questions.

    3. Match the VPN examples in:
      - Cognitive intent (what the user is trying to figure out)
      - Level of abstraction (general product language)
      - Question style (evaluative, comparative, risk-aware)

    4. Use GENERAL product language only:
      product, solution, system, service, platform.
      Avoid product-specific jargon unless absolutely necessary.

    5. Maintain the key distinction:
      - B2B questions emphasize organizational fit, scalability, governance, and justification.
      - B2C questions emphasize personal relevance, ease of use, and regret avoidance.

    6. Avoid direct comparisons between specific products, brands, or models.
    Questions should focus on evaluating a product category or solution type,
    rather than comparing two named products (e.g., do NOT generate queries like
    “Is Product A better than Product B?”).

    ==================================
    OUTPUT FORMAT
    ==================================

    Return ONLY valid JSON in the following format:

    {{
      "Awareness": {{
        "B2B": ["", "", "", ""],
        "B2C": ["", "", "", ""]
      }},
      "Consideration": {{
        "B2B": ["", "", "", ""],
        "B2C": ["", "", "", ""]
      }},
      "Decision": {{
        "B2B": ["", "", "", ""],
        "B2C": ["", "", "", ""]
      }},
      "Usage": {{
        "B2B": ["", "", "", ""],
        "B2C": ["", "", "", ""]
      }}
    }}
    """

    response = client.responses.create(
        model="gpt-5-mini-2025-08-07",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    output_text = response.output_text

    try:
        queries = json.loads(output_text)
    except:
        print("JSON parse failed:", name)
        continue

    results.append({
        "product": name,
        "user_intent": intent,
        "decision_complexity": complexity,
        "technical_level": tech,
        "queries": queries
    })

    time.sleep(2)

# ================= Save =================

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Saved to:", OUTPUT_FILE)