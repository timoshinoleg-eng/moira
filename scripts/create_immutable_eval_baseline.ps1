$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\IMYAREK\Voprosy\moira'

$diffPath = Join-Path $env:TEMP 'moira_immutable_eval_current.diff'
git diff --binary | Set-Content -NoNewline -Encoding utf8 $diffPath

$config = @{}
Get-Content '.env' | ForEach-Object {
    if ($_ -match '^(LLM_MODEL|LLM_BACKUP_MODEL|LLM_JSON_MODE|LLM_BASE_URL)=(.*)$') {
        $config[$matches[1]] = $matches[2].Trim()
    }
}

$baseline = [ordered]@{
    schema_version = 2
    run_id = 'immutable-corrected-24case-p0-2-p0-3-2026-08-17'
    created_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    commit_sha = (git rev-parse HEAD).Trim()
    branch = (git branch --show-current).Trim()
    worktree_diff_sha256 = (Get-FileHash -Algorithm SHA256 $diffPath).Hash.ToLower()
    fixture = [ordered]@{
        path = 'tests/fixtures/quality_eval_24.json'
        sha256 = (Get-FileHash -Algorithm SHA256 'tests/fixtures/quality_eval_24.json').Hash.ToLower()
        case_count = 24
    }
    harness = [ordered]@{
        sequential_runner = 'scripts/run_oracle_v6_eval.py'
        sequential_runner_sha256 = (Get-FileHash -Algorithm SHA256 'scripts/run_oracle_v6_eval.py').Hash.ToLower()
        parallel_runner = 'scripts/run_oracle_v6_eval_parallel.py'
        parallel_runner_sha256 = (Get-FileHash -Algorithm SHA256 'scripts/run_oracle_v6_eval_parallel.py').Hash.ToLower()
        adapter_sha256 = (Get-FileHash -Algorithm SHA256 'bot/llm/adapter.py').Hash.ToLower()
        p0_2_regression = 'tests/test_sol_oracle_gate_regressions.py'
        p0_2_regression_sha256 = (Get-FileHash -Algorithm SHA256 'tests/test_sol_oracle_gate_regressions.py').Hash.ToLower()
        separate_p0_3_fixture = 'tests/fixtures/oracle_p0_3_adversarial_16.json'
        separate_p0_3_fixture_sha256 = (Get-FileHash -Algorithm SHA256 'tests/fixtures/oracle_p0_3_adversarial_16.json').Hash.ToLower()
        separate_p0_3_runner = 'scripts/run_oracle_p0_3_adversarial_eval.py'
        separate_p0_3_runner_sha256 = (Get-FileHash -Algorithm SHA256 'scripts/run_oracle_p0_3_adversarial_eval.py').Hash.ToLower()
        spread_id_forwarding = $true
    }
    configuration = [ordered]@{
        model = $config['LLM_MODEL']
        backup_model = $config['LLM_BACKUP_MODEL']
        json_mode = $config['LLM_JSON_MODE']
        base_url = $config['LLM_BASE_URL']
        concurrency = 1
        note = 'Non-secret configuration only; no provider key is included.'
    }
    output_paths = [ordered]@{
        public = 'docs/QUALITY_EVAL_V6_FULL_RESULTS.json'
        private_synthetic_owner_review = 'docs/QUALITY_EVAL_V6_FULL_OWNER_REVIEW_PRIVATE.json'
    }
}

$output = 'docs/IMMUTABLE_QUALITY_EVAL_BASELINE_2026-08-17.json'
$baseline | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $output
$hash = (Get-FileHash -Algorithm SHA256 $output).Hash.ToLower()
Write-Output "BASELINE_CREATED=$output"
Write-Output "BASELINE_SHA256=$hash"
