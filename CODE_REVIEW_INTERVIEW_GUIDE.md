# Code Review Interview Guide

> **Goal**: Demonstrate technical depth, clear communication, and good judgment in 45 minutes.

## The 5-Minute Framework

### Step 1: Understand Context (2 minutes)
- Read PR title and description
- Understand the WHAT and WHY
- Note what problem this solves

### Step 2: Systematic Review (35 minutes)
Review in priority order - focus on high-impact issues first:

1. **Correctness & Security** (Critical - MUST find these)
2. **Architecture & Design** (Important - Shows depth)
3. **Testing** (Important - Shows thoroughness)
4. **Performance** (Medium - Shows experience)
5. **Code Quality** (Low - Only if egregious)

### Step 3: Write Decision (5 minutes)
- Summarize findings
- Make clear decision: APPROVE or REQUEST CHANGES
- Justify decision

### Step 4: Final Pass (3 minutes)
- Check tone (constructive, not harsh?)
- Verify specificity (line numbers, examples?)
- Balance (found positives too?)

---

## Priority 1: Correctness & Security (CRITICAL)

**These are blocking issues. Find these and you'll make a strong impression.**

### 🔴 Security Vulnerabilities

#### SQL Injection
```python
# ❌ CRITICAL: SQL injection vulnerability
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)

# Your feedback:
🔴 CRITICAL (Line 23): This query is vulnerable to SQL injection because
user input is directly interpolated into the SQL string. An attacker could
pass `1 OR 1=1` to access all users, or `1; DROP TABLE users;--` to delete
data. Use parameterized queries:
```python
query = "SELECT * FROM users WHERE id = ?"
return db.execute(query, [user_id])
```
```

#### Exposed Secrets
```python
# ❌ CRITICAL: Hardcoded credentials
API_KEY = "sk-proj-abc123xyz789"
db_password = "admin123"

# Your feedback:
🔴 CRITICAL (Lines 5-6): Hardcoded secrets in source code create security
risks - these will be committed to git history and accessible to anyone with
repo access. Move to environment variables:
```python
API_KEY = os.getenv("API_KEY")
db_password = os.getenv("DB_PASSWORD")
```
And add to .gitignore if not already there.
```

#### Missing Authentication
```python
# ❌ CRITICAL: No auth check
@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    return await db.delete_user(user_id)

# Your feedback:
🔴 CRITICAL (Line 45): This endpoint allows deleting any user without
authentication or authorization checks. Any anonymous caller could delete
users. Add authentication middleware and verify the requesting user has
permission to delete this specific user_id.
```

### 🔴 Correctness Bugs

#### Null/Undefined Handling
```python
# ❌ BUG: Potential null reference
def process_order(order):
    customer_name = order.customer.name  # customer could be None
    return f"Processing order for {customer_name}"

# Your feedback:
🔴 CRITICAL (Line 12): If order.customer is None, this will raise
AttributeError. Based on the database schema, customer is optional for
guest checkouts. Add null check:
```python
if order.customer is None:
    customer_name = "Guest"
else:
    customer_name = order.customer.name
```
```

#### Off-by-One Errors
```python
# ❌ BUG: Off-by-one
def get_last_n_items(items, n):
    return items[-n-1:]  # Wrong!

# Your feedback:
🔴 CRITICAL (Line 34): This slicing is off-by-one. For n=3, this returns 4
items because it includes index -4. Should be:
```python
return items[-n:]
```
Add test case: `assert get_last_n_items([1,2,3,4,5], 3) == [3,4,5]`
```

#### Error Handling
```python
# ❌ BUG: Swallowing exceptions
def save_user(user):
    try:
        db.save(user)
    except:
        pass  # Silent failure!

# Your feedback:
🔴 CRITICAL (Lines 18-21): This silently swallows all exceptions, making
failures invisible. If the database is down or user data is invalid, this
returns success but doesn't save anything. Either:
1. Let the exception propagate (remove try/except)
2. Log the error and re-raise
3. Return a Result type indicating success/failure

Never silently ignore errors.
```

---

## Priority 2: Architecture & Design (IMPORTANT)

**These show you understand system design and scalability.**

### 🟡 Separation of Concerns

#### Business Logic in Wrong Layer
```python
# ❌ ISSUE: Business logic in API controller
@app.post("/api/orders")
async def create_order(request: OrderRequest):
    # Validation
    if request.total < 0:
        raise HTTPException(400, "Invalid total")

    # Business logic (should be in service layer!)
    if request.total > 10000:
        discount = request.total * 0.1
    else:
        discount = 0

    final_total = request.total - discount

    # Database access (should be in repository!)
    db.execute("INSERT INTO orders VALUES (?)", [final_total])

    return {"order_id": "123"}

# Your feedback:
🟡 IMPORTANT (Lines 23-38): This endpoint contains business logic (discount
calculation) and direct database access, violating separation of concerns.
This makes the logic:
- Untestable without spinning up the API
- Not reusable from other contexts
- Hard to maintain as rules grow

Consider refactoring:
1. Move discount logic to `OrderService.calculate_discount()`
2. Move database operations to `OrderRepository.create()`
3. Keep controller thin - just coordinate between service and repository

This pattern scales better as complexity grows.
```

### 🟡 Wrong Abstraction Layer

```python
# ❌ ISSUE: Infrastructure import in domain layer
# File: domain/services/user_service.py
from infrastructure.database.models import UserModel  # Wrong layer!

class UserService:
    def create_user(self, name: str):
        user = UserModel(name=name)  # Domain depends on infrastructure!
        return user

# Your feedback:
🟡 IMPORTANT (Line 2): Domain layer is importing from infrastructure layer,
which inverts the dependency direction in hexagonal architecture. Domain
should be pure business logic with no infrastructure dependencies.

Create a domain entity (User) and repository port (UserRepositoryPort), then
inject the repository:
```python
# domain/entities/user.py
class User:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

# domain/ports/user_repository.py
class UserRepositoryPort(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        pass

# domain/services/user_service.py
class UserService:
    def __init__(self, user_repo: UserRepositoryPort):
        self.user_repo = user_repo

    async def create_user(self, name: str):
        user = User(id=generate_id(), name=name)
        return await self.user_repo.create(user)
```
This keeps domain layer testable and infrastructure-independent.
```

---

## Priority 3: Testing (IMPORTANT)

**Missing tests or poor test quality shows lack of production experience.**

### 🟡 Missing Test Coverage

```python
# ❌ ISSUE: New feature with no tests
def calculate_discount(order_total: float, user_tier: str) -> float:
    """Calculate discount based on order total and user tier."""
    if user_tier == "gold":
        return order_total * 0.2
    elif user_tier == "silver":
        return order_total * 0.1
    elif order_total > 1000:
        return order_total * 0.05
    else:
        return 0.0

# Your feedback:
🟡 IMPORTANT: This new discount calculation logic has no test coverage.
Business logic like this should have comprehensive tests covering:
- Each tier level (gold, silver, none)
- Large order discount (>$1000)
- Edge cases (total=0, total=1000 exactly, negative total)
- Invalid tier values

Suggest adding:
```python
def test_gold_tier_gets_20_percent_discount():
    assert calculate_discount(100.0, "gold") == 20.0

def test_large_order_with_no_tier_gets_5_percent():
    assert calculate_discount(1500.0, "none") == 75.0

def test_edge_case_exactly_1000_dollars():
    assert calculate_discount(1000.0, "none") == 0.0  # Not > 1000
```
```

### 🟡 Weak Tests

```python
# ❌ ISSUE: Test doesn't actually test anything
def test_create_user():
    user = create_user("Alice")
    assert user is not None  # Too vague!

# Your feedback:
🟡 IMPORTANT: This test is too vague - it only checks that something was
returned, not that it's correct. Tests should verify specific behavior:
```python
def test_create_user_returns_user_with_correct_name():
    user = create_user("Alice")
    assert user.name == "Alice"
    assert user.id is not None
    assert isinstance(user.created_at, datetime)
```

Also consider testing edge cases:
- Empty name: `create_user("")` - should it raise ValueError?
- Very long name: `create_user("A" * 1000)` - should it truncate?
- Special characters: `create_user("Alice O'Brien")` - handled correctly?
```

---

## Priority 4: Performance (MEDIUM)

**Shows you think about scale and efficiency.**

### 🟡 N+1 Query Problem

```python
# ❌ ISSUE: N+1 queries
def get_users_with_orders():
    users = db.query("SELECT * FROM users")
    result = []
    for user in users:
        # This executes a query for EACH user! (N queries)
        orders = db.query("SELECT * FROM orders WHERE user_id = ?", [user.id])
        result.append({"user": user, "orders": orders})
    return result

# Your feedback:
🟡 IMPORTANT (Lines 45-50): Classic N+1 query problem. If there are 1000
users, this executes 1001 queries (1 for users + 1000 for orders). This will
be slow and put unnecessary load on the database.

Use a JOIN or fetch all orders in one query:
```python
def get_users_with_orders():
    # Single query with JOIN
    query = """
        SELECT u.*, o.*
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id
    """
    rows = db.query(query)
    # Group by user in Python
    return group_orders_by_user(rows)
```
This reduces 1001 queries to 1, significantly improving performance.
```

### 🟡 Inefficient Algorithm

```python
# ❌ ISSUE: O(n²) when O(n) possible
def find_duplicates(items):
    duplicates = []
    for i, item in enumerate(items):
        for j, other in enumerate(items):
            if i != j and item == other and item not in duplicates:
                duplicates.append(item)
    return duplicates

# Your feedback:
🟡 IMPORTANT (Lines 12-17): This nested loop is O(n²), which will be slow
for large lists. For 10,000 items, this performs 100 million comparisons.

Use a set for O(n) solution:
```python
def find_duplicates(items):
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return list(duplicates)
```
This reduces complexity from O(n²) to O(n).
```

---

## Priority 5: Code Quality (LOW PRIORITY)

**Only mention if egregious or you've covered everything else.**

### 💡 Confusing Naming

```python
# ❌ ISSUE: Unclear naming
def process(d):
    r = []
    for x in d:
        if x[1] > 100:
            r.append(x[0])
    return r

# Your feedback:
💡 SUGGESTION (Lines 23-28): Variable names are cryptic, making the code
hard to understand. Consider more descriptive names:
```python
def get_high_value_customer_ids(orders):
    high_value_customer_ids = []
    for customer_id, order_total in orders:
        if order_total > 100:
            high_value_customer_ids.append(customer_id)
    return high_value_customer_ids
```
Or more concisely:
```python
def get_high_value_customer_ids(orders):
    return [customer_id for customer_id, total in orders if total > 100]
```
```

---

## How to Write Feedback

### The Formula

```
[SEVERITY] [LINE NUMBER]: [OBSERVATION] [IMPACT/WHY IT MATTERS] [SOLUTION]
```

### Severity Guide

| Emoji | Severity | When to Use | Example |
|-------|----------|-------------|---------|
| 🔴 | CRITICAL | Security holes, data loss, crashes | SQL injection, missing auth |
| 🟡 | IMPORTANT | Design issues, missing tests, performance | Wrong layer, N+1 queries |
| 💡 | SUGGESTION | Code quality, minor improvements | Better naming, simplification |
| ❓ | QUESTION | Need clarification or context | "Why was approach X chosen?" |
| ✅ | PRAISE | Something done well | "Nice use of X pattern" |

### Examples of Good Feedback

**❌ Bad**: "This is wrong"
**✅ Good**: "🔴 CRITICAL (Line 45): This query is vulnerable to SQL injection..."

**❌ Bad**: "Consider using a better approach"
**✅ Good**: "🟡 IMPORTANT (Lines 23-28): This N+1 query will be slow at scale. Consider using a JOIN..."

**❌ Bad**: "Rename this variable"
**✅ Good**: "💡 SUGGESTION (Line 12): `d` is unclear. Consider `discount_rate` to improve readability"

**❌ Bad**: "Why did you do this?"
**✅ Good**: "❓ QUESTION (Line 67): I see we're using approach X instead of the standard Y. Is there a specific reason for this choice? Happy to learn!"

---

## Making Your Decision

### ✅ APPROVE When:
- No critical security or correctness issues
- Any concerns are minor or optional
- Code improves the codebase overall
- Questions are curiosity, not blockers

### ❌ REQUEST CHANGES When:
- Critical issues exist (security, bugs, data loss)
- Design violates architectural principles
- Missing essential tests for new functionality
- Would introduce significant technical debt

### Your Decision Template

```markdown
## Summary
[2-3 sentences: What does this PR do? General impression?]

## Critical Issues (Must Fix) 🔴
1. [Line X]: [Specific issue with solution]
2. [Line Y]: [Specific issue with solution]

## Important Concerns (Should Address) 🟡
1. [Design/performance/testing concern]
2. [Concern with reasoning]

## Suggestions (Optional) 💡
- [Minor improvement]
- [Code quality note]

## Questions ❓
- [Clarification on approach]

## Positives ✅
- [Something done well]
- [Good pattern used]

---

## Decision: [APPROVE / REQUEST CHANGES]

**Rationale**: [1-2 sentences explaining your decision]

[If REQUEST CHANGES]: The critical issues with [X, Y] must be addressed before merging to prevent [security risk / data loss / system instability].

[If APPROVE]: While I've noted some suggestions for improvement, there are no blocking issues and this PR [improves the codebase / fixes the stated bug / adds value].
```

---

## 10 High-Impact Things to Look For

Focus your 45 minutes on these:

1. **SQL injection** - String interpolation in queries
2. **Missing authentication/authorization** - Endpoints without checks
3. **Null/undefined crashes** - Dereferencing without checks
4. **Separation of concerns** - Business logic in wrong layer
5. **N+1 queries** - Database calls in loops
6. **Missing error handling** - Try/catch that swallows exceptions
7. **Missing tests** - New functionality without coverage
8. **Hardcoded secrets** - API keys, passwords in code
9. **Error paths not tested** - Only happy path covered
10. **Wrong dependency direction** - Domain importing infrastructure

**If you find 3-5 of these kinds of issues and communicate them well, you'll do great.**

---

## Interview Strategy

### Time Management (45 minutes)
- **0-2 min**: Read PR description, understand context
- **2-25 min**: Systematic review (focus on critical issues first)
- **25-35 min**: Write feedback (in-line comments)
- **35-40 min**: Write summary and decision
- **40-45 min**: Review tone, add positives, final check

### Communication Tips

**DO**:
- ✅ Be specific (line numbers, exact issue)
- ✅ Explain impact ("this causes X problem")
- ✅ Suggest solutions (don't just complain)
- ✅ Ask questions when unsure
- ✅ Praise good things
- ✅ Use "we" language ("we could improve...")

**DON'T**:
- ❌ Be vague ("this seems off")
- ❌ Be condescending ("obviously this is wrong")
- ❌ Nitpick formatting (unless truly unreadable)
- ❌ Assume malice ("you clearly didn't think")
- ❌ Rewrite everything (respect the approach)

### Show Your Thinking

If you're unsure about something, **say so**:
- "❓ I'm not familiar with library X - is this the standard way to use it?"
- "❓ This seems like it could be a race condition, but I'd want to verify with the team's async patterns"
- "💡 This could potentially be optimized with caching, but I'm not sure if the performance matters here"

**Being honest about uncertainty is better than pretending to know everything.**

---

## Quick Reference Checklist

Print this or keep it visible during the interview:

```
CRITICAL (Find at least 1-2):
□ SQL injection vulnerabilities?
□ Hardcoded secrets/credentials?
□ Missing authentication checks?
□ Null reference crashes?
□ Swallowed exceptions?
□ Off-by-one errors?

IMPORTANT (Find 2-3):
□ Business logic in API layer?
□ N+1 query problems?
□ Missing tests for new code?
□ Weak/vague tests?
□ Wrong dependency direction?
□ Inefficient algorithms?

BONUS (If time):
□ Confusing naming?
□ Could be simplified?
□ Good patterns to praise?
```

---

## Final Tips

1. **Start with security and correctness** - These have highest impact
2. **Be thorough but not pedantic** - Find real issues, skip formatting nitpicks
3. **Always suggest solutions** - Don't just point out problems
4. **Balance criticism with praise** - Note what's done well
5. **Make a clear decision** - Don't waffle
6. **Show your reasoning** - Explain WHY something matters
7. **Ask when unsure** - Shows humility and curiosity
8. **Think about production** - "What happens when this fails?"
9. **Consider the team** - "Would I want to maintain this?"
10. **Be constructive** - You're helping, not attacking

---

## Remember

**They're not looking for perfection. They're looking for**:
- Can you spot real problems?
- Can you communicate clearly?
- Do you have good judgment about priorities?
- Would you be a good teammate?

**You don't need to find every issue. You need to find meaningful issues and communicate them well.**

Good luck! 🚀
