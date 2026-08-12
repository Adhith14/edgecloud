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

]