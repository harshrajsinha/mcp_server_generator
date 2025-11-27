# Fix indentation in ec2_setup_script.sh
$scriptPath = "C:\DAAS\MCP POC\gaurav\templates\ec2_setup_script.sh"
$content = Get-Content $scriptPath -Raw

# Define the line ranges that need fixing (lines 325-569 approximately)
# We need to reduce indentation by 4 spaces for these lines

$lines = $content -split "`r?`n"
$fixed = @()
$inCertbotBlock = $false
$blockStartLine = 324  # Approximate line where excessive indentation starts
$blockEndLine = 569    # Approximate line where it ends

for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    $lineNum = $i + 1
    
    # Detect if we're in the problematic block
    if ($lineNum -ge $blockStartLine -and $lineNum -le $blockEndLine) {
        # Remove 4 spaces of indentation if present
        if ($line -match '^                (.*)$') {
            # 16 spaces -> 12 spaces
            $fixed += "            $($matches[1])"
        }
        elseif ($line -match '^            (.*)$') {
            # 12 spaces -> 8 spaces
            $fixed += "        $($matches[1])"
        }
        elseif ($line -match '^        (.*)$') {
            # 8 spaces -> 4 spaces
            $fixed += "    $($matches[1])"
        }
        else {
            $fixed += $line
        }
    }
    else {
        $fixed += $line
    }
}

# Write back
$fixed -join "`n" | Set-Content $scriptPath -NoNewline
Write-Host "Fixed indentation in $scriptPath"
