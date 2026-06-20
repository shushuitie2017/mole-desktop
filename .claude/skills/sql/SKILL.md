---
name: sql
description: Review, optimize, or generate SQL queries and database schemas. Use when the user asks about SQL optimization, database design, query analysis, or says "sql".
disable-model-invocation: true
allowed-tools: Read, Grep, Glob
metadata:
  tier: default
  cost: light
  side_effects: none
---

Analyze or generate SQL based on the following:

$ARGUMENTS

## Capabilities

### SQL Review & Optimization
- Analyze query execution plan logic
- Identify missing indexes
- Detect N+1 query patterns
- Suggest query rewrites for better performance
- Check for proper JOIN usage

### Schema Review
- Normalization analysis
- Data type appropriateness
- Constraint completeness (PK, FK, UNIQUE, NOT NULL)
- Index strategy recommendations

### SQL Generation
- Follow the project's database conventions (naming, casing)
- Include proper indexes
- Add foreign key constraints
- Write migration scripts if the project uses them (Flyway / Liquibase / Alembic)

## Output format

For optimization:
1. **Problem**: What's inefficient
2. **Impact**: Why it matters (estimated performance impact)
3. **Solution**: Optimized query with explanation

For generation:
1. DDL statements
2. Index creation
3. Sample queries
4. Migration script if applicable
