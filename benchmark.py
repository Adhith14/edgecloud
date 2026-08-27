# ============================================================
# benchmark.py — Benchmark Task Definitions
# ============================================================
# All benchmark tasks live here as structured data. main.py
# loops over these instead of hardcoding tasks individually.
#
# FIELDS PER TASK:
#   id            - unique ID (e.g. "A1")
#   category      - category label
#   agent         - which agent handles it:
#                   file / code / planning / document / multimodal
#   description   - what the task asks (used in prompts + escalation)
#   input_type    - "log" | "document" | "text" | "image" | "multi" | "none"
#   input_ref     - the input:
#                     * single file path (for log/document/image)
#                     * inline string (for text/none)
#                     * a LIST of file paths (for input_type "multi")
#   scoring_mode  - how success is judged:
#                     "expected"      -> GEval against expected_output
#                     "execution"     -> run the code, pass if it works
#                     "criteria_only" -> GEval against criteria, no fixed answer
#                                        (used for ambiguous Category F tasks)
#   deeval_criteria   - GEval criteria text (None for execution mode)
#   expected_output   - reference answer (None for execution/criteria_only)
# ============================================================


TASKS = [

    # ════════════════════════════════════════════════════════
    # CATEGORY A — File and Log Analysis
    # ════════════════════════════════════════════════════════
    {
        "id": "A1",
        "category": "A - File/Log Analysis",
        "agent": "file_agent",
        "description": "Read the server log and extract all ERROR-level events with timestamps, then summarise the root cause in one sentence.",
        "input_type": "log",
        "input_ref": "tasks/sample_log.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the actual output correctly identifies the ERROR-level "
            "log lines and gives a sensible root cause summary. It should mention the "
            "cache connection failure and/or the payment processing timeout."
        ),
        "expected_output": (
            "The errors are: cache service connection failure after 3 retries, a "
            "NullPointerException in OrderService.processOrder(), and a payment "
            "processing timeout for order_id=9921. Root cause: cascading failures "
            "starting with the cache outage."
        ),
    },
    {
        "id": "A2",
        "category": "A - File/Log Analysis",
        "agent": "file_agent",
        "description": "Read this crash log and identify the root cause of the crash. Explain the chain of evidence in 2-3 sentences.",
        "input_type": "log",
        "input_ref": "tasks/crash_log.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output identifies the OutOfMemoryError as the crash and, "
            "crucially, links it to the leaked database connections (acquired but not returned) "
            "and rising heap usage as the underlying cause, not just the final error line."
        ),
        "expected_output": (
            "The worker crashed with an OutOfMemoryError in ReportGenerator.buildReport. The root "
            "cause is a resource leak: database connections were repeatedly acquired but never "
            "returned, and heap usage climbed from 71% to 92% until the JVM ran out of memory."
        ),
    },
    {
        "id": "A3",
        "category": "A - File/Log Analysis",
        "agent": "file_agent",
        "description": "This CSV contains system metrics sampled every 5 minutes. Identify every row that contains an abnormal value (a value far outside the typical range of that column) and state which metric is abnormal in each.",
        "input_type": "log",
        "input_ref": "tasks/metrics.csv",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output flags exactly the three anomalous rows: 09:15 (cpu_pct 88), "
            "09:20 (disk_io_mbps 95), and 09:25 (response_ms 940), naming the abnormal metric in each. "
            "Flagging normal rows or missing any of the three lowers the score."
        ),
        "expected_output": (
            "Three anomalies: at 09:15 cpu_pct spikes to 88 (normal ~30-36); at 09:20 disk_io_mbps "
            "spikes to 95 (normal ~11-14); at 09:25 response_ms spikes to 940 (normal ~99-118)."
        ),
    },
    {
        "id": "A4",
        "category": "A - File/Log Analysis",
        "agent": "file_agent",
        "description": "Summarise this server log into exactly 5 bullet points covering the most operationally important events.",
        "input_type": "log",
        "input_ref": "tasks/sample_log.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output is about 5 bullets and covers the key events: the cache "
            "service failure and fallback, the NullPointerException in OrderService, the payment "
            "timeout for order 9921, resource warnings (memory/disk), and normal recovery/backup."
        ),
        "expected_output": (
            "- Cache service connection failed and was unavailable after 3 retries, falling back to database. "
            "- NullPointerException occurred in OrderService.processOrder (line 142). "
            "- Payment processing failed for order 9921 with a 30s timeout. "
            "- Resource warnings: memory at 78% and disk at 91%. "
            "- Scheduled backup completed and health checks passed."
        ),
    },
    {
        "id": "A5",
        "category": "A - File/Log Analysis",
        "agent": "file_agent",
        "description": "Parse every ERROR-level line in this log into a JSON array. Each object must have fields: timestamp, message. Return ONLY the JSON array.",
        "input_type": "log",
        "input_ref": "tasks/sample_log.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output is valid JSON (an array of objects with timestamp and "
            "message fields) and includes the error events: cache connection failure, cache "
            "unavailable after retries, the NullPointerException, and the payment timeout."
        ),
        "expected_output": (
            '[{"timestamp": "2026-06-18 08:07:01", "message": "Failed to connect to cache service: Connection refused"}, '
            '{"timestamp": "2026-06-18 08:07:08", "message": "Cache service unavailable after 3 retries. Falling back to database."}, '
            '{"timestamp": "2026-06-18 08:13:10", "message": "NullPointerException in OrderService.processOrder() at line 142"}, '
            '{"timestamp": "2026-06-18 08:19:55", "message": "Payment processing failed for order_id=9921: Timeout after 30s"}]'
        ),
    },
     {
        "id": "A6",
        "category": "A - File/Log Analysis",
        "agent": "file_agent",
        "description": "Analyse this metrics CSV. Identify any genuine anomaly that requires investigation, and explicitly state which apparent anomalies are benign and why. Give the underlying pattern, not just the outlier rows.",
        "input_type": "log",
        "input_ref": "tasks/hard_metrics.csv",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "This task contains a deliberate trap. Determine whether the output (a) correctly "
            "dismisses the 02:30-02:45 CPU spike as benign because it is annotated as the nightly "
            "backup window, and (b) identifies the REAL problem: a sustained correlated drift from "
            "03:15 onward where memory climbs from 61 to 82 percent while error_rate rises from "
            "0.02 to 0.19 and latency_p99 rises from 124 to 286 ms, consistent with a memory leak "
            "degrading the service. An output that flags only the CPU spike, or lists rows without "
            "identifying the correlated trend, should score low regardless of presentation quality."
        ),
        "expected_output": (
            "The CPU spike at 02:30-02:45 (94% and 92%) is benign — it is annotated as the nightly "
            "backup window and CPU returns to baseline immediately afterwards. The genuine anomaly "
            "is a sustained degradation beginning around 03:15: memory rises monotonically from 61% "
            "to 82%, error_rate climbs from 0.02 to 0.19, and p99 latency increases from 124ms to "
            "286ms, while CPU stays flat at ~33%. The correlation of rising memory with rising "
            "errors and latency, without CPU involvement, indicates a probable memory leak causing "
            "progressive service degradation. This requires investigation; the backup spike does not."
        ),
    },
    {
        "id": "A7",
        "category": "A - File/Log Analysis",
        "agent": "file_agent",
        "description": "This ETL log shows several job runs and one dashboard warning. Every job reports success. Determine whether there is actually a problem, and if so explain precisely what is failing and how you can tell.",
        "input_type": "log",
        "input_ref": "tasks/silent_failure.log",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output identifies a silent failure: the ETL jobs report success "
            "and record counts are rising (47,744 -> 47,981 -> 48,213), yet the dashboard shows the "
            "customer count frozen at 44,102 for three days with its last successful refresh on "
            "2026-07-29. The correct inference is that the ETL is writing successfully but the "
            "downstream dashboard/warehouse consumer has not refreshed since 29 July, so the "
            "pipeline is broken after the load stage despite all success messages. An output that "
            "concludes there is no problem because all jobs succeeded should score very low."
        ),
        "expected_output": (
            "Yes, there is a problem, and it is a silent failure. All three ETL runs report success "
            "with rising record counts (47,744 on 30 July, 47,981 on 31 July, 48,213 on 1 August), "
            "so extract, transform and load are all working. However the dashboard warns that the "
            "customer count metric has been unchanged at 44,102 for three days, and its last "
            "successful refresh was 2026-07-29. The mismatch between rising loaded counts and a "
            "frozen reported figure shows the break is downstream of the load stage: the BI refresh "
            "or the view the dashboard reads has been failing silently since 29 July. The ETL "
            "success messages are misleading because they only cover the write, not the consumption."
        ),
    },


    # ════════════════════════════════════════════════════════
    # CATEGORY B — Code Generation and Debugging
    # ════════════════════════════════════════════════════════
    {
        "id": "B1",
        "category": "B - Code Generation",
        "agent": "code_agent",
        "description": "Write a Python function called is_prime(n) that returns True if n is prime, else False.",
        "input_type": "none",
        "input_ref": "Write a Python function called is_prime(n) that returns True if n is prime.",
        "scoring_mode": "execution",
        "deeval_criteria": None,
        "expected_output": None,
    },
    {
        "id": "B2",
        "category": "B - Code Generation",
        "agent": "code_agent",
        "description": (
            "Fix all bugs in this Python code so it runs correctly and prints the result:\n"
            "def average(nums):\n"
            "    total = 0\n"
            "    for n in nums\n"
            "        total =+ n\n"
            "    return total / len(nums)\n"
            "\n"
            "print(average([2, 4, 6]))"
            'Return the complete corrected script, including the function definition and the print statement.'
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "execution",
        "deeval_criteria": None,
        "expected_output": None,
    },
    {
        "id": "B3",
        "category": "B - Code Generation",
        "agent": "code_agent",
        "description": (
            "Write a function fizzbuzz(n) that returns 'Fizz' for multiples of 3, 'Buzz' for "
            "multiples of 5, 'FizzBuzz' for multiples of both, and str(n) otherwise. Then write "
            "at least 4 test functions using assert statements, and call all the tests at the end."
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "execution",
        "deeval_criteria": None,
        "expected_output": None,
    },
    {
        "id": "B4",
        "category": "B - Code Generation",
        "agent": "code_agent",
        "description": (
            "Refactor this code to be cleaner and shorter without changing its behaviour. "
            "It must remain runnable and print the same output:\n"
            'Return the complete corrected script, including the function definition and the print statement.'
            "def calc(x):\n"
            "    if x > 0:\n"
            "        if x % 2 == 0:\n"
            "            r = x * 2\n"
            "        else:\n"
            "            r = x * 3\n"
            "    else:\n"
            "        if x % 2 == 0:\n"
            "            r = x * 2\n"
            "        else:\n"
            "            r = x * 3\n"
            "    return r\n"
            "print(calc(4))\n"
            "print(calc(5))"
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "execution",
        "deeval_criteria": None,
        "expected_output": None,
    },
    {
        "id": "B5",
        "category": "B - Code Generation",
        "agent": "code_agent",
        "description": (
            "Given tables orders(id, customer_id, amount, created_at) and customers(id, name, country), "
            "write a single SQL query returning the total order amount per country for the year 2026, "
            "highest total first. Return ONLY the SQL."
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the SQL joins orders to customers on customer_id, filters created_at "
            "to the year 2026, groups by country, sums amount, and orders by the total descending."
        ),
        "expected_output": (
            "SELECT c.country, SUM(o.amount) AS total_amount FROM orders o JOIN customers c "
            "ON o.customer_id = c.id WHERE o.created_at >= '2026-01-01' AND o.created_at < '2027-01-01' "
            "GROUP BY c.country ORDER BY total_amount DESC;"
        ),
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY C — Planning and Task Decomposition
    # ════════════════════════════════════════════════════════
    {
        "id": "C1",
        "category": "C - Planning",
        "agent": "planning_agent",
        "description": "Decompose into ordered subtasks: build a data pipeline that reads CSV files, cleans the data, and outputs a summary report.",
        "input_type": "text",
        "input_ref": "Build a data pipeline that reads CSV files, cleans the data, and outputs a summary report.",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the actual output decomposes the goal into logical, "
            "ordered subtasks covering reading CSVs, cleaning/validating data, and "
            "generating a summary report."
        ),
        "expected_output": (
            "1. Read CSV files. 2. Validate and clean the data. 3. Perform analysis. "
            "4. Generate a summary report. 5. Output the report."
        ),
    },
    {
        "id": "C2",
        "category": "C - Planning",
        "agent": "planning_agent",
        "description": "Break down the goal 'add user authentication to an existing web application' into a prioritised, ordered task list covering backend, frontend, database, and testing work.",
        "input_type": "text",
        "input_ref": "Add user authentication (register, login, logout, password reset) to an existing web application with a React frontend, Flask backend, and PostgreSQL database.",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the plan is ordered and covers all four areas: database changes "
            "(users table, password hashing), backend (auth endpoints, sessions or tokens), "
            "frontend (forms, protected routes), and testing. Order should be logical "
            "(database/backend before frontend integration)."
        ),
        "expected_output": (
            "1. Design users table with hashed passwords. 2. Implement backend register/login/logout "
            "endpoints with password hashing and session or JWT tokens. 3. Add password reset flow "
            "with tokenised email links. 4. Build frontend register/login forms and wire to the API. "
            "5. Add protected routes and auth state handling in React. 6. Write unit and integration "
            "tests for auth endpoints and flows."
        ),
    },
    {
        "id": "C3",
        "category": "C - Planning",
        "agent": "planning_agent",
        "description": "A web application intermittently returns 500 errors for roughly 5% of requests, with no obvious pattern. Produce a step-by-step investigation plan to find the cause.",
        "input_type": "text",
        "input_ref": "Symptoms: ~5% of requests return HTTP 500, intermittent, no clear pattern by time, endpoint, or user. Stack: nginx, Flask app with 4 workers, PostgreSQL.",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the plan is a logical, ordered investigation: examining error logs and "
            "stack traces first, correlating failures (endpoint, worker, timing, payload), checking "
            "resource limits and database connections, and forming/testing a hypothesis. Generic "
            "advice without an ordered method scores lower."
        ),
        "expected_output": (
            "1. Pull application error logs and collect stack traces for the 500s. 2. Correlate failures "
            "by endpoint, worker process, request payload, and time to find hidden patterns. 3. Check "
            "nginx and Flask worker logs for timeouts or restarts. 4. Inspect database connection pool "
            "usage and slow queries during failures. 5. Check memory/CPU limits per worker. 6. Form a "
            "hypothesis (e.g. pool exhaustion under concurrent load), reproduce under load testing, "
            "then apply and verify a fix."
        ),
    },
    {
        "id": "C4",
        "category": "C - Planning",
        "agent": "planning_agent",
        "description": "You manage a team of specialist AI agents: a file agent (reads/analyses files), a code agent (writes code), a document agent (summarises/extracts), and a vision agent (reads images). Delegate the following job into subtasks, assigning each subtask to the correct agent in order: 'Read the attached error screenshot, find the matching stack trace in the server log, and write a patched version of the failing function.'",
        "input_type": "text",
        "input_ref": "Job: read an error screenshot, locate the matching stack trace in a server log, and write a patched version of the failing function.",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the delegation is correct and ordered: vision agent first (read the "
            "screenshot), then file agent (search the log for the matching trace), then code agent "
            "(write the patch). Assigning wrong agents or wrong order lowers the score."
        ),
        "expected_output": (
            "1. Vision agent: read the error screenshot and extract the error message. 2. File agent: "
            "search the server log for the stack trace matching that error and identify the failing "
            "function. 3. Code agent: write a patched version of the failing function addressing the "
            "root cause."
        ),
    },
    {
        "id": "C5",
        "category": "C - Planning",
        "agent": "planning_agent",
        "description": "Outline the components required for a small REST API service with user authentication and a database layer. For each component, state its responsibility in one line.",
        "input_type": "text",
        "input_ref": "Design target: a small REST API with authentication and persistent storage, deployable on a single server.",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the outline includes the essential components with sensible one-line "
            "responsibilities: API/routing layer, authentication (tokens or sessions), business logic, "
            "data access layer, database, and configuration/deployment concerns. Missing auth or the "
            "database layer scores low."
        ),
        "expected_output": (
            "API routing layer: receives HTTP requests and maps them to handlers. Auth middleware: "
            "validates tokens/sessions on protected routes. Business logic layer: implements core "
            "operations. Data access layer: mediates all database queries. Database (e.g. PostgreSQL): "
            "persistent storage. Config and deployment: environment variables, migrations, and a "
            "process manager or container."
        ),
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY D — Document Processing
    # ════════════════════════════════════════════════════════
    {
        "id": "D1",
        "category": "D - Document Processing",
        "agent": "document_agent",
        "description": "Summarise the provided document in 2-3 sentences.",
        "input_type": "document",
        "input_ref": "tasks/sample_document.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the actual output is a faithful 2-3 sentence summary of "
            "the edge computing document, mentioning local processing and at least one "
            "benefit (privacy or latency) or challenge (limited compute)."
        ),
        "expected_output": (
            "Edge computing processes data locally rather than in the cloud, reducing "
            "latency and protecting privacy. However, local devices have limited "
            "compute resources."
        ),
    },
    {
        "id": "D2",
        "category": "D - Document Processing",
        "agent": "document_agent",
        "description": "Produce a structured outline of this report with a heading for each section and one line summarising each section's key point.",
        "input_type": "document",
        "input_ref": "tasks/report_document.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the outline covers all four sections (Overview, Reliability, Cost "
            "Optimisation, Outlook) with an accurate one-line summary of each: growth and spend, "
            "the two incidents and availability miss, the shutdown savings plan, and Q3 priorities."
        ),
        "expected_output": (
            "Overview: requests up 18% to 4.2M/day, spend up 11% to £142,000. Reliability: 99.87% "
            "availability missed the 99.9% target, with two incidents (load balancer misconfiguration, "
            "slow database failover). Cost Optimisation: 23% of compute spend is idle non-production "
            "usage; automated shutdown from August projected to save £8,500/quarter. Outlook: Q3 "
            "priorities are the shutdown rollout, failover under 5 minutes, and reserved capacity for "
            "analytics (~30% cost reduction)."
        ),
    },
    {
        "id": "D3",
        "category": "D - Document Processing",
        "agent": "document_agent",
        "description": "Extract every named entity from this report into three lists: people, organisations, and dates. Include monetary figures as a fourth list.",
        "input_type": "document",
        "input_ref": "tasks/report_document.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output correctly lists: person Sarah Okafor; organisation "
            "NorthBridge Software Ltd; dates 8 July 2026, 14 May 2026, 23 June 2026 (and August 2026); "
            "and figures £142,000 and £8,500. Missing entities or inventing ones lowers the score."
        ),
        "expected_output": (
            "People: Sarah Okafor. Organisations: NorthBridge Software Ltd. Dates: 8 July 2026, "
            "14 May 2026, 23 June 2026, August 2026. Monetary figures: £142,000, £8,500."
        ),
    },
    {
        "id": "D4",
        "category": "D - Document Processing",
        "agent": "document_agent",
        "description": "Using ONLY this policy document, answer these three questions: (1) How many days per week can a full-time employee work remotely? (2) Within what timeframe must lost equipment be reported? (3) What are the core hours?",
        "input_type": "document",
        "input_ref": "tasks/policy_document.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether all three answers are correct and grounded in the document: up to 3 "
            "days per week; within 24 hours to IT Security; core hours 10:00 to 16:00 local time."
        ),
        "expected_output": (
            "1. Up to 3 days per week. 2. Within 24 hours, reported to IT Security. 3. 10:00 to 16:00 "
            "local time."
        ),
    },
    {
        "id": "D5",
        "category": "D - Document Processing",
        "agent": "document_agent",
        "description": "Classify this document into exactly one of these categories: technical report, HR policy, marketing material, legal contract, meeting minutes. State the category and justify in one sentence.",
        "input_type": "document",
        "input_ref": "tasks/policy_document.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output classifies the document as HR policy (the only correct "
            "category) with a sensible one-sentence justification referencing its content (remote "
            "working rules, eligibility, equipment, availability)."
        ),
        "expected_output": (
            "HR policy — the document defines company rules for employee remote working, covering "
            "eligibility, equipment, security obligations, and availability requirements."
        ),
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY E — Multimodal
    # ════════════════════════════════════════════════════════
    {
        "id": "E1",
        "category": "E - Multimodal",
        "agent": "multimodal_agent",
        "description": "Analyse the provided screenshot and describe any errors or issues, then suggest a fix.",
        "input_type": "image",
        "input_ref": "tasks/error_screenshot.png",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output identifies the SPECIFIC error shown in the image "
            "(naming the failing command and why it failed) and suggests a concrete fix. "
            "Generic troubleshooting advice that does not name the actual error, or that "
            "could apply to any screenshot, should score low regardless of how well written it is."
        ),
        "expected_output": (
            "The screenshot shows a PowerShell error: the command 'la' is not recognised as a "
            "cmdlet, function, or operable program. 'la' is a Unix alias for 'ls -a' and does not "
            "exist in PowerShell. Fix: use 'ls' or 'Get-ChildItem -Force', or define an alias with "
            "Set-Alias la Get-ChildItem."
        ),
    },
    {
        "id": "E2",
        "category": "E - Multimodal",
        "agent": "multimodal_agent",
        "description": "Read this bar chart. State which expense category has the single highest bar and which economical class it belongs to, state which class spends the most on housing, and describe in one sentence how spending patterns differ between the classes.",
        "input_type": "image",
        "input_ref": "tasks/chart.png",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output correctly reads the grouped bar chart: that the tallest "
            "bar is Rich spending on Food (~5500 GBP), that the Poor class spends the most on "
            "Housing (~4000 GBP), and that it describes the inverted pattern — poorer classes spend "
            "proportionally more on housing while the rich class spends far more on food. Values "
            "within roughly 500 GBP are acceptable. Naming the wrong category or class, or inventing "
            "values not in the chart, should score low."
        ),
        "expected_output": (
            "Determine whether the output correctly reads the grouped bar chart: that the tallest "
            "bar is Rich spending on Food, and that the Poor class spends the most on Housing. "
            "Correctly identifying these two facts is the primary requirement. Stating approximate "
            "values and describing the comparative pattern between classes are secondary and should "
            "add to the score but their absence should not fail an otherwise correct reading. "
            "Naming the wrong category or class, or inventing values not in the chart, should score low."
        ),
    },
    {
        "id": "E3",
        "category": "E - Multimodal",
        "agent": "multimodal_agent",
        "description": "Describe the system architecture shown in this diagram. It compares two builds. List the components of each build and explain what differs between them.",
        "input_type": "image",
        "input_ref": "tasks/diagram.png",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output identifies that the diagram compares two builds (v1 "
            "current and v2 target), names the shared three-layer structure (Cloud CEO at top, an "
            "agent swarm in the middle, an evaluation layer at the bottom), and correctly states "
            "the key differences in v2: specialist models per agent rather than one shared model, "
            "a shared tool layer, and links between agents. Describing only one side, or missing "
            "the comparison entirely, should score low."
        ),
        "expected_output": (
            "The diagram compares two builds side by side. Both share a three-layer structure: a "
            "Cloud CEO at the top that plans and delegates, an agent swarm in the middle, and an "
            "evaluation layer at the bottom. In v1 (current build) the local swarm has four agents "
            "— file, code, planning, and document — all sharing one model (qwen2.5:3b), with no "
            "tools and agents running in isolation, feeding into DeepEval plus escalation. In v2 "
            "(target build) the specialist swarm assigns a different model to each role (qwen2.5-coder "
            "for code, llama3.2:3b for file, qwen2.5:3b for docs, gpt-4o in the cloud for vision), "
            "adds a shared tool layer providing read_file, run_code and search, connects the agents "
            "to each other, and feeds an evaluation and experiment layer supporting sweeps, graphs "
            "and trade-offs."
        ),
    },
    {
        "id": "E4",
        "category": "E - Multimodal",
        "agent": "multimodal_agent",
        "description": "Extract the table in this image into CSV format. Include the header row. Return ONLY the CSV, no commentary.",
        "input_type": "image",
        "input_ref": "tasks/data_table.png",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output is valid CSV whose headers and cell values match the "
            "spreadsheet in the image: seven columns (StudentID, First name, Last name, Math, "
            "Phonics, Science, Attendance) and ten student rows. Score proportionally to accuracy — "
            "missing rows, transposed columns, misread numbers, or commentary wrapped around the "
            "CSV should reduce the score."
        ),
        "expected_output": (
            "StudentID,First name,Last name,Math,Phonics,Science,Attendance\n"
            "1,Jessica,Brookins,85,96,76,210\n"
            "2,Matt,Nama,80,54,95,215\n"
            "3,Betty,Chu,90,67,94,200\n"
            "4,Cara,Mina,75,82,34,180\n"
            "5,Jen,Caro,78,56,56,218\n"
            "6,Lisa,Pedro,91,78,73,218\n"
            "7,Jin,Liu,63,90,89,210\n"
            "8,Molly,Vans,78,82,56,205\n"
            "9,Samatha,Summers,69,66,87,180\n"
            "10,Jake,Crane,95,72,67,210"
        ),
    },
    {
        "id": "E5",
        "category": "E - Multimodal",
        "agent": "multimodal_agent",
        "description": "This screenshot shows Python source code and an error traceback together. Identify the exception type, state which line of the visible code raises it, explain the true underlying cause, and give the corrected code.",
        "input_type": "image",
        "input_ref": "tasks/complex_error.png",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "This task requires combining two regions of the image, not just reading text. "
            "Determine whether the output (a) names KeyError: 'q4' as the exception, (b) notes it "
            "is raised at line 15 in quarter_total, and crucially (c) identifies that the real "
            "cause is line 9 of SALES_DATA where the 'west' region is missing its q4 entry while "
            "all other regions have four quarters, and (d) gives a valid fix. An answer that only "
            "reads the traceback and blames line 15 without tracing back to the missing data should "
            "score low, as should generic debugging advice."
        ),
        "expected_output": (
            "The exception is KeyError: 'q4', raised at line 15 in quarter_total where it executes "
            "'return region_data[quarter]'. That line is not the actual fault. The real cause is in "
            "the SALES_DATA dictionary at line 9: the 'west' region only defines q1, q2 and q3, "
            "while north, south and east each define all four quarters. Since annual_total loops "
            "over ['q1','q2','q3','q4'] for every region, the lookup fails when it reaches q4 for "
            "west. The traceback confirms the call chain: build_report (line 31) calls annual_total "
            "(line 23) which calls quarter_total (line 15). Fix: add the missing q4 value to the "
            "west region, for example \"west\": {\"q1\": 8200, \"q2\": 9100, \"q3\": 8800, \"q4\": 9500}. "
            "A more defensive fix would use region_data.get(quarter, 0) to tolerate missing quarters."
        ),
    },


    # ════════════════════════════════════════════════════════
    # CATEGORY F — Real-World Ambiguous Tasks
    # (scoring_mode: criteria_only — no single correct answer)
    # ════════════════════════════════════════════════════════
    {
        "id": "F1",
        "category": "F - Ambiguous",
        "agent": "file_agent",
        "description": "The deployment failed last night. Look at the log and figure out what happened.",
        "input_type": "log",
        "input_ref": "tasks/sample_log.txt",
        "scoring_mode": "criteria_only",
        "deeval_criteria": (
            "The request is deliberately vague. Determine whether the actual output "
            "makes a reasonable interpretation of what 'failed' means, identifies "
            "plausible issues from the log, and clearly states any assumptions it made. "
            "A good answer handles the ambiguity sensibly rather than asking for "
            "clarification or producing nothing useful."
        ),
        "expected_output": None,
    },
    {

        "id": "F2",
        "category": "F - Ambiguous",
        "agent": "code_agent",
        "description": (
            "Clean up this function:\n"
            "def proc(d):\n"
            "    r = []\n"
            "    for i in range(len(d)):\n"
            "        if d[i] != None:\n"
            "            if d[i] > 0:\n"
            "                r.append(d[i] * 2)\n"
            "    return r\n"
            "print(proc([1, None, -2, 3]))"

        ),

        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "criteria_only",
        "deeval_criteria": (

            "The request is vague — 'clean up' is undefined. Determine whether the output makes a "
            "reasonable interpretation (readability, idiomatic Python such as direct iteration and "
            "'is not None', possibly a comprehension), keeps the behaviour identical, and ideally "
            "states what it chose to improve. Any sensible cleanup counts; changing behaviour or "
            "producing non-runnable code scores low."
        ),

        "expected_output": None,

    },

    {

        "id": "F3",
        "category": "F - Ambiguous",
        "agent": "planning_agent",
        "description": "Can you help me get this project moving? It's been stalled for a while.",
        "input_type": "text",
        "input_ref": "A software side-project has been stalled for two months. No further details are provided about the project's type, state, or team.",
        "scoring_mode": "criteria_only",
        "deeval_criteria": (

            "The request gives almost no information. Determine whether the output handles this "
            "sensibly: stating its assumptions, asking a small number of clarifying questions or "
            "offering a general re-start framework (assess current state, identify blockers, define "
            "one next milestone, timebox work). Generic motivational filler with no actionable "
            "structure scores low; a structured, assumption-aware response scores high."
        ),

        "expected_output": None,

    },

    {

        "id": "F4",
        "category": "F - Ambiguous",
        "agent": "document_agent",
        "description": "Something's off with this report — take a look.",
        "input_type": "document",
        "input_ref": "tasks/report_document.txt",
        "scoring_mode": "criteria_only",
        "deeval_criteria": (

            "The request does not say what kind of issue to find. Determine whether the output "
            "examines the report critically and surfaces at least one legitimate observation (e.g. "
            "availability missed its target, incident response was slow, rising costs, idle "
            "non-production spend) and states the interpretation it took. Vague replies that just "
            "summarise the report without identifying anything 'off' score low."
        ),

        "expected_output": None,

    },

    {

        "id": "F5",
        "category": "F - Ambiguous",
        "agent": "document_agent",
        "description": "Summarise the important parts of this document.",
        "input_type": "document",
        "input_ref": "tasks/policy_document.txt",
        "scoring_mode": "criteria_only",
        "deeval_criteria": (

            "'Important' is undefined. Determine whether the output makes a defensible selection of "
            "what matters most (eligibility limits, security obligations, the 24-hour reporting rule, "
            "core hours) rather than reproducing everything or picking trivia. Stating the basis for "
            "selection is a plus. A copy of the whole document or a random subset scores low."
        ),

        "expected_output": None,

    },

    # ════════════════════════════════════════════════════════
    # CATEGORY G — Complex Multi-Step Tasks
    # (input_type: multi — multiple input files)
    # ════════════════════════════════════════════════════════
    {
        "id": "G1",
        "category": "G - Complex Multi-Step",
        "agent": "file_agent",
        "description": "You are given three separate service logs. Correlate the errors across all three to identify a single shared root cause, and explain the chain of failures.",
        "input_type": "multi",
        "input_ref": [
            "tasks/service_a.log",
            "tasks/service_b.log",
            "tasks/service_c.log",
        ],
       "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the actual output correlates errors across all three "
            "logs rather than treating them in isolation, identifies the database "
            "REINDEX operation and its exclusive lock as the originating cause, and "
            "explains the cascade: lock -> connection pool exhaustion -> order-service "
            "timeouts -> api-gateway 502 errors."
        ),
        "expected_output": (
            "A scheduled REINDEX on the inventory table in inventory-db took an ACCESS "
            "EXCLUSIVE lock at 09:14:00, blocking queries. This exhausted the 20-connection "
            "pool by 09:14:38. order-service workers then blocked waiting for connections "
            "and its queries timed out at 09:14:40. api-gateway saw upstream timeouts and "
            "returned 502 errors from 09:14:47, opening its circuit breaker. Everything "
            "recovered once the REINDEX finished at 09:17:38."
        ),
    },
    {
        "id": "G2",
        "category": "G - Complex Multi-Step",
        "agent": "planning_agent",
        "description": "Decompose the feature 'add user authentication' into subtasks across backend, frontend, database, and testing — AND for each subtask, state which must be completed before which (the dependency order). Present as a numbered list with an explicit dependencies line per item.",
        "input_type": "text",
        "input_ref": "Feature: user authentication (register, login, logout) for a React + Flask + PostgreSQL application. Deliverable: subtasks with explicit dependency ordering.",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output covers all four areas AND states explicit dependencies "
            "(e.g. frontend forms depend on backend endpoints; endpoints depend on the users table). "
            "A flat list without dependency statements scores low even if the subtasks are right."
        ),
        "expected_output": (
            "1. Create users table with hashed password column (no dependencies). 2. Backend register/"
            "login/logout endpoints with hashing and sessions (depends on 1). 3. Frontend register and "
            "login forms wired to the API (depends on 2). 4. Protected routes and auth state in React "
            "(depends on 3). 5. Unit tests for endpoints (depends on 2). 6. Integration tests for the "
            "full flow (depends on 3 and 4)."
        ),
    },
    {
        "id": "G3",
        "category": "G - Complex Multi-Step",
        "agent": "code_agent",
        "description": (
            "Complete ALL THREE parts in one response: (1) write a Python function "
            "count_words(text) that returns a dict of word frequencies, lowercased, ignoring "
            "punctuation; (2) write at least 3 assert-based tests for it and call them; "
            "(3) write a docstring for the function documenting parameters, return value, and one example."
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "execution",
        "deeval_criteria": None,
        "expected_output": None,
    },
    {
        "id": "G4",
        "category": "G - Complex Multi-Step",
        "agent": "file_agent",
        "description": "Read this pipeline definition and its last run output, then answer: which stage introduced the fault the finance team is complaining about, what exactly went wrong, and what fix would you apply? Note carefully: a stage can report OK and still be the culprit.",
        "input_type": "log",
        "input_ref": "tasks/broken_pipeline.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output identifies the enrich stage as the fault origin (the "
            "country join produced NULLs for 2,141 rows — but more importantly the aggregate output "
            "collapsed to ONE row, meaning the join failed for effectively all rows), reasons that "
            "'OK' status hid the failure, and proposes a sensible fix (fix the join key/data, fail "
            "the pipeline on NULL-country thresholds). Blaming aggregate or publish alone scores low."
        ),
        "expected_output": (
            "The fault originates in the enrich stage: its country join failed, leaving country NULL "
            "— and since the final summary contains only one row with all £312,449 under NULL, the "
            "join effectively failed for all rows despite the stage reporting OK. The aggregate and "
            "publish stages then faithfully processed bad data. Fix: repair the join (key mismatch or "
            "empty/changed customers source), and add a validation gate that fails the pipeline when "
            "NULL-country rows exceed a small threshold."
        ),
    },
    {
        "id": "G5",
        "category": "G - Complex Multi-Step",
        "agent": "file_agent",
        "description": "You are given three inputs: a service's config file, a PagerDuty alert, and the service's log. Determine what went wrong, whether any configuration value contributed to the impact, and recommend one config change with justification.",
        "input_type": "multi",
        "input_ref": [
            "tasks/app_config.yaml",
            "tasks/incident_error.txt",
            "tasks/service_b.log",
        ],
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output connects the three inputs: the alert's 502 spike at 09:14, "
            "the log showing DB pool exhaustion and 4000ms query timeouts, and the config's "
            "pool_size: 20 and timeout_ms: 4000 as the relevant settings. A good answer recommends a "
            "justified config change (e.g. raise pool_size, tune timeout, or add circuit-breaking) "
            "tied to the evidence. Treating the inputs separately without connecting them scores low."
        ),
        "expected_output": (
            "The incident was database connection pool exhaustion in order-api: the log shows workers "
            "blocked waiting on connections and queries timing out at 4000ms, matching the config's "
            "pool_size: 20 and timeout_ms: 4000, which produced the 502 spike in the alert at 09:14. "
            "The pool size and timeout directly shaped the impact. Recommended change: increase "
            "database pool_size (e.g. 20 → 40) — or better, add early load-shedding — because the "
            "20-connection ceiling was saturated while 8 workers each held connections during slow "
            "queries, and justify by monitoring pool utilisation after the change."
        ),
    },
    {
        "id": "G6",
        "category": "G - Complex Multi-Step",
        "agent": "document_agent",
        "description": "Three sources are provided about a rollback procedure. An engineer is about to perform a rollback based on one of them. Determine whether their plan is safe, identify any conflict between the sources, state which source is authoritative and why, and give the correct procedure.",
        "input_type": "document",
        "input_ref": "tasks/conflicting_docs.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "This task requires reconciling contradictory sources by recency and authority. "
            "Determine whether the output (a) identifies that the runbook from January 2025 is "
            "outdated, (b) recognises the June 2026 post-mortem supersedes it and mandated a paired "
            "migration rollback plus DBA approval for release 4.2 and later, (c) concludes that "
            "Alice's plan in the July Slack thread is UNSAFE because she is rolling back to 4.1 "
            "from a 4.2-or-later release and is following the stale runbook, and (d) gives the "
            "corrected procedure. An output that accepts the runbook at face value, or that merely "
            "summarises the three documents without resolving the conflict, should score low."
        ),
        "expected_output": (
            "The engineer's plan is unsafe. The runbook (last edited January 2025) states that "
            "payments-api rollbacks require code only, with on-call approval. That guidance is "
            "outdated. The post-mortem dated 3 June 2026 records that exactly this procedure failed "
            "during the 2 June incident, because release 4.2 introduced a non-backward-compatible "
            "schema change to the transactions table; rolling back code alone left the service "
            "unable to read that table. The completed action item requires a paired migration "
            "rollback and DBA approval for any rollback of release 4.2 or later. The post-mortem is "
            "authoritative because it is the most recent source and its action item was completed. "
            "In the Slack thread Alice is rolling back to 4.1 from a later release while following "
            "the stale runbook, so she would reproduce the June failure. The correct procedure is to "
            "roll back the application code AND the associated database migration together, with "
            "DBA approval obtained first."
        ),
    },
    {
        "id": "G7",
        "category": "G - Complex Multi-Step",
        "agent": "file_agent",
        "description": "You are given a metrics CSV and an ETL log from overlapping time periods. Determine whether the two datasets describe related problems or independent ones, justify your conclusion with specific evidence from both, and state what a responsible engineer should investigate first.",
        "input_type": "multi",
        "input_ref": [
            "tasks/hard_metrics.csv",
            "tasks/silent_failure.log",
        ],
        "scoring_mode": "expected",
        "deeval_criteria": (
            "This task tests whether the model resists false correlation. The two files describe "
            "DIFFERENT systems (an api service showing memory-leak-like degradation, and an etl/BI "
            "pipeline with a stale dashboard) at different dates and times. Determine whether the "
            "output correctly concludes the problems are INDEPENDENT, citing concrete evidence such "
            "as different services, non-overlapping dates, and unrelated failure signatures. An "
            "output that manufactures a causal link between the api degradation and the ETL/dashboard "
            "issue should score low, however confidently it is argued."
        ),
        "expected_output": (
            "The two datasets describe independent problems. The metrics CSV covers the 'api' "
            "service between 02:00 and 05:00 and shows a progressive degradation — memory rising "
            "from 61% to 82% with error_rate rising to 0.19 and p99 latency to 286ms while CPU "
            "stays flat — consistent with a memory leak. The ETL log covers a different system, "
            "daily_customer_sync writing to the warehouse on 30 July to 1 August, where all jobs "
            "succeed with rising record counts but the BI dashboard has been frozen at 44,102 since "
            "its last refresh on 29 July. The services differ, the failure signatures are unrelated, "
            "and there is no shared component or timestamp linking them. A responsible engineer "
            "should treat them separately and prioritise the api degradation first, since it is "
            "actively worsening and affecting live request latency and error rates, whereas the "
            "dashboard staleness affects reporting only."
        ),
    },
    {
        "id": "G8",
        "category": "G - Complex Multi-Step",
        "agent": "code_agent",
        "description": (
            "Complete all three parts and return one runnable Python script: "
            "(1) write a function detect_drift(rows) that takes a list of dicts with keys "
            "'mem_pct' and 'error_rate' and returns the index of the first row where BOTH "
            "memory and error rate have increased for three consecutive readings, or -1 if "
            "no such point exists; "
            "(2) write at least four assert-based tests including an edge case where drift "
            "never occurs and one where the data is shorter than four rows; "
            "(3) run all the tests at the end so execution prints a confirmation line."
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "execution",
        "deeval_criteria": None,
        "expected_output": None,
    },
    
    # ════════════════════════════════════════════════════════
    # CATEGORY H — Chained Multi-Agent Tasks
    # These require more than one specialist. The supervisor
    # decomposes them and routes subtasks to different agents.
    # ════════════════════════════════════════════════════════
    {
        "id": "H1",
        "category": "H - Chained Multi-Agent",
        "agent": "file_agent",          # fallback if chaining is disabled
        "chain": True,
        "description": (
            "The file buggy_report.py contains a Python script with a bug. "
            "Read it, identify the bug, produce a corrected version of the "
            "script, and verify the corrected version runs without error."
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output identifies the actual bug — the 'west' "
            "region in SALES_DATA is missing its 'q4' entry while annual_total "
            "loops over all four quarters, causing KeyError: 'q4' — and provides "
            "a corrected script that would run. Blaming the lookup line in "
            "quarter_total without tracing back to the missing data should score "
            "lower. Generic error-handling advice without identifying the data "
            "gap should score low."
        ),
        "expected_output": (
            "The bug is in SALES_DATA: the 'west' region defines only q1, q2 and "
            "q3, while annual_total iterates over q1 to q4 for every region, so "
            "quarter_total raises KeyError: 'q4' when it reaches west. The fix is "
            "to add the missing q4 value for west, or to use "
            "region_data.get(quarter, 0) so missing quarters are tolerated. The "
            "corrected script runs and prints an annual total for all four regions."
        ),
    },
    {
        "id": "H2",
        "category": "H - Chained Multi-Agent",
        "agent": "file_agent",
        "chain": True,
        "description": (
            "Read the server log sample_log.txt, extract the error events, then "
            "write and run a Python script that counts how many errors occurred "
            "per hour. Report both the errors you found and the counts your "
            "script produced."
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "This task requires reading a file AND writing working code. Determine "
            "whether the output (a) identifies the error events from the log, "
            "including the cache connection failure, the NullPointerException and "
            "the payment timeout, and (b) reports per-hour counts derived from "
            "actual code rather than asserted from memory. All the errors occur "
            "within the 08:00 hour, so a correct count groups them there."
        ),
        "expected_output": (
            "The log contains error events at 08:07:01 (cache service connection "
            "refused), 08:07:08 (cache unavailable after 3 retries), 08:13:10 "
            "(NullPointerException in OrderService.processOrder, with stack trace) "
            "and 08:19:55 (payment processing timeout for order 9921). All fall "
            "within the 08:00 hour, so the per-hour count is: 08:00 -> 4 or 5 "
            "errors depending on whether the stack trace line is counted separately."
        ),
    },
    {
        "id": "H3",
        "category": "H - Chained Multi-Agent",
        "agent": "document_agent",
        "chain": True,
        "description": (
            "Read the quarterly report report_document.txt. Extract the monetary "
            "figures it contains, then write and run a Python script that "
            "calculates what percentage of the quarterly infrastructure spend the "
            "projected savings represent. Report the figures and the calculated "
            "percentage."
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the output extracts the correct figures from the "
            "report — total quarterly spend of GBP 142,000 and projected savings "
            "of GBP 8,500 per quarter — and reports a calculated percentage of "
            "approximately 6% (8500/142000 = 5.99%). Wrong figures, or a "
            "percentage not matching the figures given, should score low."
        ),
        "expected_output": (
            "The report gives total infrastructure spend for the quarter as "
            "GBP 142,000 and projected savings from the automated shutdown policy "
            "as GBP 8,500 per quarter. The savings represent approximately 6.0% "
            "of quarterly spend (8,500 / 142,000 = 5.99%)."
        ),
    },
    {
        "id": "H4",
        "category": "H - Chained Multi-Agent",
        "agent": "file_agent",
        "chain": True,
        "description": (
            "Read the three service logs service_a.log, service_b.log and "
            "service_c.log. Determine the root cause of the incident, then produce "
            "a remediation plan listing the steps an engineering team should take "
            "to prevent it recurring."
        ),
        "input_type": "none",
        "input_ref": "",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "This requires log analysis followed by planning. Determine whether "
            "the output (a) identifies the root cause: a scheduled REINDEX taking "
            "an exclusive lock on the inventory table, exhausting the database "
            "connection pool, which blocked order-service workers and caused "
            "api-gateway 502 errors, and (b) provides a concrete remediation plan "
            "addressing that cause, such as scheduling reindex operations off-peak, "
            "using concurrent reindexing, increasing pool capacity, or adding "
            "circuit breaking. A plan that does not follow from the identified "
            "cause should score low."
        ),
        "expected_output": (
            "Root cause: a scheduled REINDEX on the inventory table took an ACCESS "
            "EXCLUSIVE lock at 09:14:00, blocking queries and exhausting the "
            "20-connection pool by 09:14:38. order-service workers then blocked "
            "waiting for connections and its queries timed out, and api-gateway "
            "returned 502 errors from 09:14:47 until recovery at 09:17:38. "
            "Remediation: schedule reindex operations during genuine low-traffic "
            "windows or use CONCURRENT reindexing to avoid exclusive locks; "
            "increase connection pool headroom; add circuit breaking and load "
            "shedding in order-service so pool exhaustion degrades gracefully; "
            "add alerting on pool utilisation and lock wait times so the condition "
            "is detected before user impact."
        ),
    },

]