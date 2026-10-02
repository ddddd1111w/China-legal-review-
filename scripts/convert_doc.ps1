# 批量将旧版 .doc 通过本机 Word COM 转换为 .docx（供 sync_library.py 调用）
# 用法: powershell -ExecutionPolicy Bypass -File convert_doc.ps1 -JobsFile <jobs.json>
# jobs.json: [{"doc": "绝对路径.doc", "docx": "输出绝对路径.docx"}, ...]
# 结果以 JSON 行打印到 stdout: {"doc":..., "ok":true} 或 {"doc":..., "ok":false,"error":...}
param(
    [Parameter(Mandatory = $true)][string]$JobsFile
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$jobs = Get-Content $JobsFile -Encoding UTF8 -Raw | ConvertFrom-Json

$word = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0  # wdAlertsNone
} catch {
    # Word 不可用时尝试 WPS
    try {
        $word = New-Object -ComObject KWPS.Application
        $word.Visible = $false
        $word.DisplayAlerts = 0
    } catch {
        foreach ($j in $jobs) {
            @{ doc = $j.doc; ok = $false; error = "Word/WPS COM 均不可用" } | ConvertTo-Json -Compress
        }
        exit 1
    }
}

# wdFormatXMLDocument = 12
foreach ($j in $jobs) {
    $doc = $null
    try {
        $outDir = Split-Path $j.docx -Parent
        if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
        # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles)
        $doc = $word.Documents.Open($j.doc, $false, $true, $false)
        $doc.SaveAs([ref]$j.docx, [ref]12)
        $doc.Close($false)
        $doc = $null
        @{ doc = $j.doc; ok = $true } | ConvertTo-Json -Compress
    } catch {
        if ($doc -ne $null) { try { $doc.Close($false) } catch {} }
        @{ doc = $j.doc; ok = $false; error = "$($_.Exception.Message)" } | ConvertTo-Json -Compress
    }
}

$word.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
exit 0
