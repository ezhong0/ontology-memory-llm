# Code Review Interview Guide - Founding Engineer Role

> **Critical Context**: This is a FOUNDING ENGINEER role. They're not just evaluating your technical skills - they're asking: "Will this person set the right trajectory for our company?"

## What This Interview Is Really About

The interview guide explicitly states three signals:
1. **Technical depth** - Can you spot issues that will bite us in production?
2. **Communication** - Can you give feedback that makes the team better?
3. **Judgment** - Can you make good trade-off decisions?

**Judgment is the most important.** Anyone can find bugs. Founding engineers need to know:
- What's critical vs. what's a nitpick?
- When "good enough to ship" is the right call vs. when "we need to fix this first"
- When to push back vs. when to let things go
- How to balance speed and quality

---

## The Founding Engineer Mindset

### Think Like an Owner, Not a Code Reviewer

**❌ Code Reviewer Mindset**:
- "This violates clean architecture principles"
- "We should refactor this for better maintainability"
- "This could be more elegant"

**✅ Founding Engineer Mindset**:
- "Will this cause production issues or can we ship it?" (Risk assessment)
- "Does this block us from iterating quickly or is it fine for now?" (Speed vs. quality)
- "Will this make future features harder or is it isolated?" (Technical debt evaluation)
- "Is this the right problem to solve right now?" (Prioritization)

### The Startup Context

Early-stage startups operate differently:
- **Speed matters** - Getting to product-market fit is priority #1
- **Perfect is the enemy of shipped** - Over-engineering is a real risk
- **Technical debt is a tool** - Strategic debt is fine, reckless debt is not
- **Team standards matter** - You're setting patterns for future engineers

### What They're Really Testing

When you review code, they're asking:

**Technical Depth**:
- Can you spot security holes? (Critical - will cause real damage)
- Can you spot correctness bugs? (Critical - will break production)
- Do you understand architecture? (Important - shows system thinking)
- Do you know performance patterns? (Good to have - shows experience)

**Communication**:
- Are you constructive or just critical?
- Do you explain WHY things matter?
- Do you suggest solutions, not just problems?
- Would people want to work with you?

**Judgment** (Most Important):
- Can you distinguish "ship-blocking" from "nice-to-have"?
- Do you understand trade-offs between speed and quality?
- Can you think about business impact, not just code quality?
- Do you know when to push back vs. when to approve?

---

## The 45-Minute Strategy

### Format Expectations

The guide says: "Utilize in-line code comments to communicate your detailed feedback"

This means **GitHub PR review format**:
- In-line comments on specific lines (like GitHub's review feature)
- Overall summary at the end
- Clear APPROVE or REQUEST CHANGES decision

### Time Breakdown

**Minutes 0-3: Understand the Business Context**
- What problem is this solving?
- Why is this change needed?
- What's the customer impact?
- Is this on the critical path?

**Minutes 3-25: Systematic Review (In Priority Order)**

Focus on what actually matters:

1. **Critical Issues (5-8 min)**: Will break production or cause security holes
   - Security vulnerabilities
   - Correctness bugs
   - Data loss risks

2. **Important Issues (8-12 min)**: Will cause problems down the line
   - Architecture violations
   - Missing tests
   - Performance problems at scale

3. **Judgment Calls (5-8 min)**: Need trade-off decisions
   - Is this technical debt acceptable?
   - Does this pattern scale?
   - Is this the right abstraction?

**Minutes 25-40: Write In-Line Comments**
- Use GitHub-style in-line comments
- Be specific with line numbers
- Suggest solutions, not just problems

**Minutes 40-45: Write Overall Summary & Decision**
- Summarize key concerns
- Make clear decision with rationale
- Show you understand the business context

---

## Priority 1: Critical Issues (Ship-Blocking)

**These are non-negotiable. Find these and call them out strongly.**

### 🔴 Security Vulnerabilities

These will cause real damage in production. Always blocking.

#### SQL Injection
```python
# Line 23-25
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
```

**Your in-line comment:**
```
🔴 BLOCKING: SQL injection vulnerability

This query directly interpolates user input, allowing an attacker to execute arbitrary SQL:
- Input: `1 OR 1=1` → Returns all users
- Input: `1; DROP TABLE users;--` → Deletes the table

This is a critical security hole that must be fixed before merging.

**Fix**: Use parameterized queries:
```python
query = "SELECT * FROM users WHERE id = ?"
return db.execute(query, [user_id])
```

**Why it matters**: SQL injection is #1 on OWASP Top 10. This could lead to complete database compromise.
```

#### Exposed Secrets
```python
# Line 5-6
API_KEY = "sk-proj-abc123xyz789"
STRIPE_SECRET = "sk_live_51abc..."
```

**Your in-line comment:**
```
🔴 BLOCKING: Hardcoded secrets in source code

These credentials will be committed to git history and accessible to anyone with repo access. This is a security breach waiting to happen.

**Impact**: If this repo is ever compromised or shared, these API keys give full access to our systems.

**Fix**:
1. Move to environment variables: `API_KEY = os.getenv("API_KEY")`
2. Rotate these keys immediately (they're now in git history)
3. Add `.env` to `.gitignore` if not already there
4. Consider using a secrets manager (AWS Secrets Manager, Vault, etc.)

**For now**: At minimum, move to .env file before merging.
```

#### Missing Authentication
```python
# Line 45-47
@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    return await db.delete_user(user_id)
```

**Your in-line comment:**
```
🔴 BLOCKING: No authentication or authorization

This endpoint allows anyone to delete any user without authentication. An attacker could delete all user accounts.

**What's missing**:
1. Authentication: Who is making this request?
2. Authorization: Do they have permission to delete this specific user?

**Fix**: Add auth middleware and permission check:
```python
@app.delete("/api/users/{user_id}")
@require_auth  # Verify user is logged in
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    # Only admins or the user themselves can delete
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(403, "Not authorized")
    return await db.delete_user(user_id)
```

**Why it matters**: This is a P0 security hole. Must fix before shipping.
```

### 🔴 Correctness Bugs

These will break production. Blocking unless low-risk.

#### Null/None Handling
```python
# Line 12-13
def process_order(order):
    customer_name = order.customer.name
    return f"Processing order for {customer_name}"
```

**Your in-line comment:**
```
🔴 BLOCKING: Null reference error for guest checkouts

Looking at the schema, `order.customer` is optional (guests don't have customer records). This will crash with AttributeError on guest orders.

**Impact**: Every guest checkout will fail with a 500 error.

**Fix**:
```python
def process_order(order):
    customer_name = order.customer.name if order.customer else "Guest"
    return f"Processing order for {customer_name}"
```

**Question**: Are guest checkouts a core flow? If yes, this is definitely blocking. If it's edge case we're not supporting yet, we could add validation to reject guest orders earlier with a clear error.
```

#### Silent Failures
```python
# Line 18-21
def save_user(user):
    try:
        db.save(user)
    except:
        pass  # Ignore errors
```

**Your in-line comment:**
```
🔴 BLOCKING: Silent failure hides critical errors

This swallows ALL exceptions, making failures invisible:
- Database down? Returns success, but nothing saved
- Invalid data? Returns success, but nothing saved
- Network error? Returns success, but nothing saved

**Impact**: Data loss with no visibility. Users will think their actions succeeded when they didn't.

**Fix Options**:
1. **Remove try/except** - Let exceptions propagate (simplest)
2. **Log and re-raise** - For observability:
```python
try:
    db.save(user)
except Exception as e:
    logger.error("Failed to save user", user_id=user.id, error=str(e))
    raise
```

**Why it matters**: Silent data loss is one of the worst bugs. Users lose trust immediately.
```

---

## Priority 2: Important Issues (Should Fix)

**These will cause problems but might not be ship-blocking depending on context.**

### 🟡 Architecture & Design Issues

#### Business Logic in Wrong Layer
```python
# Line 23-38
@app.post("/api/orders")
async def create_order(request: OrderRequest):
    # Discount calculation in API endpoint
    if request.total > 10000:
        discount = request.total * 0.1
    else:
        discount = 0

    final_total = request.total - discount
    db.execute("INSERT INTO orders VALUES (?)", [final_total])
    return {"order_id": "123"}
```

**Your in-line comment:**
```
🟡 SHOULD FIX: Business logic in API layer

This mixes three concerns in one endpoint:
1. HTTP handling (request/response)
2. Business logic (discount calculation)
3. Data access (direct DB call)

**Why this matters**:
- Can't test discount logic without spinning up the API
- Can't reuse discount logic from batch jobs or other contexts
- As discount rules grow (multiple tiers, promo codes, etc.), this endpoint becomes a mess
- Direct DB access in controller makes it hard to swap databases or add caching

**Refactoring suggestion**:
```python
# api/routes/orders.py
@app.post("/api/orders")
async def create_order(request: OrderRequest, order_service: OrderService):
    order = await order_service.create_order(request.total)
    return {"order_id": order.id}

# domain/services/order_service.py
class OrderService:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    async def create_order(self, total: float) -> Order:
        discount = self._calculate_discount(total)
        final_total = total - discount
        return await self.order_repo.create(final_total)

    def _calculate_discount(self, total: float) -> float:
        return total * 0.1 if total > 10000 else 0
```

**Trade-off consideration**: This refactoring takes time. Questions:
- How often will discount logic change? (If frequently, worth refactoring now)
- Are we adding promo codes soon? (If yes, refactor now to avoid rewrite)
- Is this MVP code we're testing with users? (If yes, maybe ship as-is and refactor after validation)

**Recommendation**: If this is core business logic we'll iterate on, refactor now. If it's MVP throwaway code, shipping as-is is reasonable with a TODO.
```

### 🟡 Performance Issues

#### N+1 Query Problem
```python
# Line 45-50
def get_users_with_orders():
    users = db.query("SELECT * FROM users")
    result = []
    for user in users:
        orders = db.query("SELECT * FROM orders WHERE user_id = ?", [user.id])
        result.append({"user": user, "orders": orders})
    return result
```

**Your in-line comment:**
```
🟡 PERFORMANCE: N+1 query problem

This executes 1 + N queries (1 for users, then 1 per user for orders). With 1000 users, that's 1001 queries.

**Impact assessment**:
- If this endpoint is called frequently → Big problem, will slow down significantly
- If users count is < 100 → Probably fine for MVP, optimize later
- If this is for admin dashboard used once a day → Not urgent

**Fix** (when needed):
```python
def get_users_with_orders():
    query = """
        SELECT u.*, o.*
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id
    """
    rows = db.query(query)
    return group_by_user(rows)  # Group in Python
```
This reduces to 1 query regardless of user count.

**Question**: What's the expected usage pattern? If this is an admin endpoint with <100 users, I'd approve shipping as-is and optimize if it becomes a bottleneck. If it's user-facing with growth expected, fix before launch.

**Judgment call**: Depends on context. Not automatically blocking.
```

---

## Priority 3: Judgment Calls (Startup Context)

**This is where you show founding engineer thinking.**

### Technical Debt Decisions

#### Example: Quick Implementation vs. Scalable Design
```python
# Line 67-80
def send_notification(user_id: str, message: str):
    # TODO: For now, just email. Later add push, SMS, etc.
    user = get_user(user_id)
    send_email(user.email, message)
```

**Your in-line comment:**
```
💡 DESIGN DECISION: Simple notification approach

Current implementation is email-only. The TODO mentions adding push/SMS later.

**Trade-off analysis**:

**Pros of current approach**:
- Simple, easy to understand
- Gets notifications working today
- No over-engineering

**Cons of current approach**:
- Adding push/SMS later requires changing every call site
- No abstraction for "notification channel"
- Will be refactor-heavy if we add channels soon

**Questions to consider**:
- Is multi-channel notifications on the roadmap for next 1-2 sprints?
- How many places call send_notification()?

**Recommendation**:
- **If multi-channel is 2+ months away**: Ship as-is, YAGNI principle applies
- **If it's on the roadmap for next month**: Consider a simple abstraction now:

```python
class NotificationService:
    def send(self, user_id: str, message: str, channel: str = "email"):
        if channel == "email":
            self._send_email(user_id, message)
        # Easy to add push/SMS later without changing call sites
```

This is 10 minutes of work now that saves hours of refactoring later.

**My take**: Given the TODO, I'd lean toward the simple abstraction. But if we're validating product-market fit and multi-channel is speculative, shipping as-is is totally reasonable.

**Not blocking** - either approach is defensible depending on priorities.
```

### When to Approve Despite Issues

#### Example: MVP Code With Known Limitations
```python
# Line 120-135
def calculate_pricing(items: List[Item]) -> float:
    # HACK: Hardcoded pricing for MVP
    # TODO: Move to pricing table when we have dynamic pricing
    total = 0
    for item in items:
        if item.type == "basic":
            total += 10
        elif item.type == "premium":
            total += 25
    return total
```

**Your in-line comment:**
```
✅ ACCEPTABLE MVP APPROACH: Hardcoded pricing

This is explicitly marked as MVP code with clear TODO. The hack is:
- **Intentional** (not accidental)
- **Documented** (clear TODO)
- **Isolated** (one function, easy to replace)
- **Adequate** (works for current needs)

**When this becomes a problem**:
- When we need to change prices without deploying code
- When we add 5+ item types (gets unwieldy)
- When we need A/B testing on pricing

**What makes this acceptable**:
✅ Clear comment explaining it's temporary
✅ Isolated to one function (easy to replace)
✅ Solves the immediate problem
✅ Doesn't create security/correctness issues

**Suggestion**: Add a ticket number to the TODO so we track when to refactor:
```python
# TODO [PRICING-123]: Move to pricing table when we have dynamic pricing
```

**Verdict**: This is smart pragmatism. Shipping MVP code that solves today's problem while being easy to refactor later is exactly the right call.

**APPROVE** - This is good engineering for an early-stage startup.
```

---

## Priority 4: Tests (Context-Dependent)

### When Missing Tests Are Blocking

```python
# Line 89-102
def charge_customer(customer_id: str, amount: float) -> bool:
    """Charge customer's saved payment method."""
    customer = get_customer(customer_id)
    payment_method = customer.default_payment_method

    result = stripe.charge(
        amount=amount,
        payment_method=payment_method.id
    )

    return result.success
```

**Your in-line comment:**
```
🔴 BLOCKING: No tests for payment logic

This is core business logic that handles money. Missing tests is not acceptable here, even for MVP.

**Why this is blocking**:
- Bugs in payment logic directly cost money
- No way to verify edge cases (no payment method, charge fails, network error)
- Can't refactor safely later without tests

**Required test coverage**:
```python
def test_charge_customer_success():
    # Happy path: charge succeeds

def test_charge_customer_no_payment_method():
    # Customer has no saved payment method

def test_charge_customer_charge_fails():
    # Stripe returns failure (declined card)

def test_charge_customer_stripe_error():
    # Stripe API throws exception (network error)
```

**Judgment**: Payment logic is never "move fast and break things" territory. Need tests before shipping.

**Request**: Add tests before merging.
```

### When Missing Tests Are Acceptable

```python
# Line 45-52
def format_user_display_name(user: User) -> str:
    """Format user's name for display in UI."""
    if user.preferred_name:
        return user.preferred_name
    elif user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    else:
        return user.email.split("@")[0]
```

**Your in-line comment:**
```
💡 OPTIONAL: Tests would be nice but not blocking

This is pure presentation logic with no business impact. Bugs here just mean slightly wrong display names.

**Risk assessment**:
- Low impact: Wrong display name is annoying but not breaking
- Simple logic: Easy to verify by inspection
- UI layer: Will be caught in manual testing

**Tests would help**:
```python
def test_format_user_display_name_preferred():
    user = User(preferred_name="Bob", first_name="Robert")
    assert format_user_display_name(user) == "Bob"
```

But not having them isn't a blocker for MVP.

**Recommendation**:
- **If you have time**: Add quick tests (5 min)
- **If you're rushing to launch**: Ship without, add tests in next sprint

**APPROVE without tests** - This is the kind of code where test ROI is lower for early stage.
```

---

## How to Write In-Line Comments (GitHub Style)

### The Format They Expect

```
[EMOJI + SEVERITY] [SUMMARY HEADLINE]

[Why this matters - impact/risk]

[What to do about it - specific solution]

[Optional: Questions or trade-off discussion]
```

### Comment Templates

#### Critical Issue Template
```
🔴 BLOCKING: [What's wrong]

**Impact**: [What breaks in production]

**Fix**:
[Specific code suggestion]

**Why this can't wait**: [Business/security risk]
```

#### Important Issue Template
```
🟡 SHOULD FIX: [What's wrong]

**Why this matters**: [Long-term problem this creates]

**Suggested approach**:
[Specific refactoring]

**Trade-off**: [Time vs. benefit]

**Recommendation**: [Your judgment call]
```

#### Suggestion Template
```
💡 SUGGESTION: [Improvement idea]

**Current**: [What code does now]
**Alternative**: [Better approach]
**Benefit**: [Why it's better]

**Not blocking** - [Why this is optional]
```

#### Question Template
```
❓ QUESTION: [What you're wondering]

[Explain your thinking]

[Why you're asking]

**If [X], then [recommendation]**
**If [Y], then [different recommendation]**
```

#### Praise Template
```
✅ NICE: [What's done well]

[Why this is good - specific reason]

[What it enables or prevents]
```

---

## Your Final Summary Template

After in-line comments, write an overall summary:

```markdown
## 📋 Review Summary

### What This PR Does
[2-3 sentences on the purpose and approach]

### Overall Assessment
[Your high-level take: Is this good work? Does it solve the problem? Any major concerns?]

---

## 🔴 Critical Issues (Must Fix Before Merge)

1. **[Line X]: SQL injection in user query**
   - Fix: Use parameterized queries
   - Risk: Complete database compromise

2. **[Line Y]: Missing auth on delete endpoint**
   - Fix: Add authentication middleware
   - Risk: Anyone can delete any user

[If none: "None found - no security or correctness blockers."]

---

## 🟡 Important Concerns (Should Address)

1. **[Lines X-Y]: Business logic in API layer**
   - Impact: Hard to test and reuse
   - Suggestion: Extract to service layer
   - Trade-off: Takes 30 min, saves hours later
   - **Judgment**: [Blocking or not? Explain reasoning]

2. **[Line Z]: N+1 query problem**
   - Impact: Will be slow with many users
   - Question: What's the expected usage?
   - **Judgment**: [Blocking if user-facing, acceptable if admin dashboard]

[If none: "None found - architecture looks solid for current stage."]

---

## 💡 Suggestions (Optional Improvements)

- **[Line A]**: Could simplify with list comprehension (readability)
- **[Line B]**: Consider extracting magic number to constant (maintainability)

[These are nice-to-haves, not blockers]

---

## ✅ Things Done Well

- **[Line X]**: Excellent error handling with specific exceptions
- **[Line Y]**: Good use of type hints throughout
- **Overall**: Clean, readable code that solves the problem

[Always include positives - shows you're not just a critic]

---

## ❓ Questions

1. **[Line X]**: Is the hardcoded pricing temporary for MVP or will this approach scale?
   - If temporary → Approve as-is
   - If long-term → Need pricing table

2. **[Line Y]**: Are we planning to add more notification channels soon?
   - If yes → Add abstraction now
   - If no → YAGNI, ship as-is

---

## 🎯 Decision: [APPROVE / REQUEST CHANGES]

### Rationale

[REQUEST CHANGES example:]
**REQUEST CHANGES**: The SQL injection (Line 23) and missing authentication (Line 45) are critical security holes that must be fixed before merging. These could lead to complete system compromise. Once these are addressed, happy to approve.

The architectural concerns are worth discussing but not blocking - we can refactor as we grow.

[APPROVE example:]
**APPROVE**: While I've noted some suggestions for improvement, there are no blocking security or correctness issues. This PR solves the stated problem and the code quality is solid.

The hardcoded pricing is explicitly marked as MVP-temporary and isolated to one function - smart pragmatism for early stage. The missing tests on formatting logic are low-risk given it's pure presentation.

Good work overall. Let's ship it and iterate.

---

## 💭 Founding Engineer Perspective

[Optional section showing you think about bigger picture]

**What I like about this approach**:
- Solves the immediate problem
- Code is readable and maintainable
- Clear TODOs for future improvements

**What I'd watch as we grow**:
- Refactor pricing logic when we hit 5+ item types
- Add monitoring on the X endpoint (no tests currently)
- Consider extraction pattern for Y when we add similar features

**For future PRs**:
- Payment logic should always have tests (involves money)
- Security-sensitive endpoints need extra scrutiny
- When in doubt on architecture, let's discuss trade-offs as a team
```

---

## 10 High-Impact Things to Find

Focus your review on these (in priority order):

### Must Find (Blocking):
1. **SQL injection** - String interpolation in queries
2. **Exposed secrets** - Hardcoded API keys, passwords
3. **Missing auth** - Endpoints that should require authentication
4. **Null crashes** - Dereferencing without null checks in critical paths
5. **Silent failures** - Try/except that swallows exceptions

### Should Find (Context-Dependent):
6. **Business logic in wrong layer** - Logic that should be testable
7. **N+1 queries** - Especially in user-facing endpoints
8. **Missing tests on critical paths** - Payment, auth, data integrity
9. **Architecture violations** - That will make future work harder
10. **Performance problems** - That will impact user experience

### Nice to Find (Shows depth):
11. **Good patterns to praise** - Shows you're not just critical
12. **Trade-off discussions** - Shows you think about context
13. **Thoughtful questions** - Shows curiosity and humility

---

## The Judgment Framework

**When deciding if something is blocking, ask:**

### 1. What's the Risk?
- **High Risk** (Security, data loss, crashes) → Blocking
- **Medium Risk** (Architecture debt, performance) → Context-dependent
- **Low Risk** (Style, minor improvements) → Not blocking

### 2. What's the Context?
- **Is this MVP code testing product-market fit?** → Higher tolerance for debt
- **Is this core infrastructure other features depend on?** → Lower tolerance
- **Is this temporary or permanent?** → Temporary hacks are more acceptable
- **How hard is this to change later?** → Easy to change = less urgent

### 3. What's the Business Impact?
- **Does this block users?** → Blocking
- **Does this slow development?** → Important but maybe not blocking
- **Does this cost money?** → Blocking (payment bugs, inefficient APIs)
- **Does this affect user trust?** → Blocking (security, data integrity)

### 4. What's the Trade-Off?
- **Time to fix vs. risk of not fixing** → Is it worth the delay?
- **Complexity added vs. flexibility gained** → Is abstraction worth it?
- **Perfect now vs. good enough + iterate** → What's right for this stage?

### Example Decisions

**Scenario**: N+1 query in admin dashboard used by 2 people once a day
- Risk: Low (not user-facing, small scale)
- Context: MVP, not on critical path
- Business impact: Minimal
- Trade-off: Fixing takes time, benefit is small
- **Decision: APPROVE** with suggestion to optimize later

**Scenario**: N+1 query in user feed endpoint
- Risk: High (user-facing, scales with users)
- Context: Core feature, will get worse as we grow
- Business impact: Slow UX, high DB load costs
- Trade-off: Must fix, this will bite us
- **Decision: REQUEST CHANGES**

**Scenario**: Business logic in API for MVP feature
- Risk: Medium (hard to test, hard to reuse)
- Context: MVP code, testing product hypothesis
- Business impact: Slows future iteration if we keep this feature
- Trade-off: Extract now (30 min) vs. refactor later (2 hours)
- **Decision: APPROVE with TODO** if clearly marked as temporary, **REQUEST CHANGES** if treating as permanent

---

## Common Founding Engineer Scenarios

### Scenario 1: "Move Fast But This Is Hacky"

```python
# TODO: This is hacky but gets us to launch. Refactor after we validate PMF.
def process_payment(amount):
    # Simplified logic for MVP
    return stripe.charge(amount)
```

**Bad Response**: "This is hacky and violates clean architecture. Request changes."

**Good Response**:
```
💡 PRAGMATIC APPROACH: Simplified payment logic for MVP

The TODO is clear about this being temporary for validation.

**What makes this acceptable**:
- Explicitly marked as MVP code
- Solves the immediate need (can take payments)
- Isolated (easy to replace without touching other code)

**What would make this NOT acceptable**:
- If we're handling complex payment flows (refunds, subscriptions)
- If this processes high volume (needs error handling, retries)
- If there's no plan to revisit (no TODO, treating as permanent)

**Questions**:
1. What's "after we validate PMF" - 3 months? 6 months? Just curious for planning.
2. Are we tracking refunds/failures anywhere for manual handling?

**Verdict**: This is smart MVPing. Ship it, validate, refactor when you have signal.

✅ APPROVE
```

### Scenario 2: "Perfect Architecture vs. Ship Now"

**PR Description**: "Quick implementation to unblock customer demo tomorrow. Can refactor after."

**Bad Response**: Focus only on architectural purity, ignore business context.

**Good Response**:
```
## Summary

I understand this is needed for a customer demo tomorrow. I'll focus on must-fix issues vs. nice-to-haves.

## 🔴 Must Fix Before Demo
[Only critical security/correctness issues that would embarrass us in demo]

## 🟡 Can Wait Until After Demo
[Architecture improvements that matter but won't affect demo]

## Decision: REQUEST CHANGES (only for critical), APPROVE (if no critical issues)

**If APPROVE**: "No blockers for the demo. I've noted some refactoring ideas for after you close the deal. Good luck with the customer! 🚀"
```

### Scenario 3: Over-Engineering

```python
# PR adds complex abstraction layer for feature used in one place
class NotificationStrategyFactory:
    def create_strategy(self, channel: str) -> INotificationStrategy:
        if channel == "email":
            return EmailNotificationStrategy()
        # ... 50 lines of strategy pattern setup
```

**Your comment**:
```
❓ QUESTION: Abstraction seems heavy for current needs

Looking at the codebase, we only send email notifications from 2 places. This adds:
- 5 new classes
- Strategy pattern complexity
- Harder to understand for new engineers

**YAGNI principle**: "You Ain't Gonna Need It" - we shouldn't abstract until we have 2-3 concrete use cases.

**Simpler approach** that's easier to maintain:
```python
def send_notification(user_id: str, message: str, channel: str = "email"):
    if channel == "email":
        send_email(user_id, message)
    # When we add push/SMS, add elif here (2 lines vs. new classes)
```

**Trade-off**:
- Current PR: More "architected" but harder to understand
- Simpler approach: Easy to understand, easy to extend when needed

**Question**: Are we planning to add 5+ notification channels soon? If yes, maybe this makes sense. If no, I'd vote for simplicity.

**Recommendation**: Start simple, refactor when we actually need the flexibility. For now, YAGNI.

💡 Not blocking, but worth discussing: Are we over-engineering this?
```

---

## Red Flags vs. Green Flags

### 🚩 Red Flags (When to REQUEST CHANGES)

**Security/Correctness**:
- SQL injection vulnerabilities
- Hardcoded secrets in code
- Missing authentication on sensitive endpoints
- Null reference crashes on main paths
- Silent exception swallowing

**Architecture (Context-Dependent)**:
- Will make future work significantly harder
- Creates tight coupling across the codebase
- Mixes concerns in a way that's hard to untangle

**Shows Poor Judgment**:
- Over-engineering simple problems
- No tests on critical paths (payments, auth)
- Ignoring obvious edge cases

### 🟢 Green Flags (Shows Good Engineering)

**Smart Pragmatism**:
- Clear TODOs marking temporary code
- MVPs that solve today's problem
- Isolated hacks that are easy to replace

**Good Communication**:
- PR description explains the "why"
- Comments explain non-obvious decisions
- Asks for feedback on trade-offs

**Quality Signals**:
- Tests on critical paths
- Error handling with logging
- Type hints and clear naming

---

## The "Would I Want to Work With This Person?" Test

Throughout your review, ask yourself: **"If I wrote this PR, would I want this person reviewing it?"**

### ✅ Good Teammate Signals

**Constructive**:
- Points out problems AND suggests solutions
- Explains why things matter, not just "this is wrong"
- Balances criticism with praise

**Judgment**:
- Understands context and trade-offs
- Knows when to push back vs. when to let go
- Thinks about business impact, not just code purity

**Communication**:
- Clear, specific feedback with line numbers
- Asks questions when unsure
- Uses "we" language ("we could improve") not "you" language ("you did this wrong")

### ❌ Bad Teammate Signals

**Pedantic**:
- Nitpicks every small thing
- Ignores context and constraints
- Perfect is the enemy of done

**Harsh**:
- Critical without constructive suggestions
- Condescending tone
- No recognition of good work

**Dogmatic**:
- "This violates principle X" without discussing trade-offs
- Insists on perfection regardless of stage
- Doesn't consider business context

---

## Final Checklist

Print this and keep it visible during your interview:

```
□ Read PR description - understand the WHY
□ Consider business context - demo tomorrow? MVP? Core infrastructure?

CRITICAL (Must find if present):
□ SQL injection or other security holes?
□ Hardcoded secrets?
□ Missing authentication?
□ Null crashes on main paths?
□ Silent exception swallowing?

IMPORTANT (Context-dependent):
□ Architecture violations that block future work?
□ N+1 queries on user-facing endpoints?
□ Missing tests on critical paths (payments, auth)?
□ Performance problems that affect UX?

JUDGMENT:
□ Did I consider trade-offs, not just point out issues?
□ Did I distinguish blocking from nice-to-have?
□ Did I think about business impact?
□ Did I suggest solutions, not just problems?

COMMUNICATION:
□ Are my comments specific (line numbers)?
□ Did I explain WHY things matter?
□ Did I praise good work?
□ Is my tone constructive?
□ Would I want me reviewing my code?

DECISION:
□ Clear APPROVE or REQUEST CHANGES?
□ Rationale explains reasoning?
□ Considered business context?
```

---

## Key Takeaways

### What They're Really Looking For

1. **Technical Depth**: Can you spot real problems before they hit production?
2. **Communication**: Can you make engineers better through feedback?
3. **Judgment**: Can you make good trade-off decisions under constraints?

### What Sets Founding Engineers Apart

**Average engineer**: Finds bugs, points out violations
**Founding engineer**: Finds bugs, assesses risk, considers context, suggests solutions, makes judgment calls

### The One Thing to Remember

> **You're not a code cop checking compliance. You're a founding engineer evaluating: "Is this the right trade-off for where we are as a company right now?"**

That's the mindset that will make you stand out.

---

Good luck! You've got this. 🚀

Remember: They want to know if you can **set the right trajectory** for their company. Show them you can balance speed and quality, find real issues, and think like an owner.
