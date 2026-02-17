$ErrorActionPreference = "Stop"

$goalId = [guid]::NewGuid().ToString()
$agentId = [guid]::NewGuid().ToString()

Write-Host "Creating goal..."
$goalPayload = @{
  goal_id = $goalId
  intent = "Create social launch and deploy analytics service"
  constraints = @("stay under budget")
  budget = 120
  deadline = (Get-Date).ToUniversalTime().AddDays(1).ToString("o")
  risk_tolerance = "medium"
  domains = @("social", "dev")
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "http://localhost:8100/v1/goals" -ContentType "application/json" -Body $goalPayload | Out-Null

Write-Host "Creating agent..."
$agentPayload = @{
  agent_id = $agentId
  name = "autopilot-1"
  capabilities = @("social.publish", "dev.pipeline", "ops.observe")
  domains = @("social", "dev")
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "http://localhost:8100/v1/agents" -ContentType "application/json" -Body $agentPayload | Out-Null

Write-Host "Executing agent..."
$executePayload = @{
  intent = "Run launch and deploy service"
  goal_id = $goalId
  policy = @{
    tool_allowances = @("social.publish", "dev.pipeline", "ops.observe")
    resource_limits = @{
      max_cpu = "4"
      max_memory = "8Gi"
      max_runtime_seconds = 1200
    }
    network_scope = "internet"
    data_scope = "standard"
    rollback_policy = "on_failure"
  }
} | ConvertTo-Json -Depth 8

$exec = Invoke-RestMethod -Method Post -Uri "http://localhost:8100/v1/agents/$agentId/execute" -ContentType "application/json" -Body $executePayload
$exec | ConvertTo-Json -Depth 10

Write-Host "Seeding and listing incidents..."
Invoke-RestMethod -Method Post -Uri "http://localhost:8100/v1/incidents/_seed" | Out-Null
Invoke-RestMethod -Method Get -Uri "http://localhost:8100/v1/incidents" | ConvertTo-Json -Depth 8

