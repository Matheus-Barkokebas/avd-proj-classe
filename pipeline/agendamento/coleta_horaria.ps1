# Coleta do COP de hora em hora (indicadores e rios) e, às 06h, as camadas diárias.
# O servidor do COP só responde a IPs do Brasil, por isso roda numa máquina local, não no GitHub Actions.
# Veja em agendamento/README.md como registrar no Agendador de Tarefas do Windows.
$pipeline = Split-Path -Parent $PSScriptRoot
$python = Join-Path $pipeline ".venv\Scripts\python.exe"
$script = Join-Path $pipeline "src\ingestao\cop_recife.py"
$log = Join-Path $pipeline "data\coleta_horaria.log"

Set-Location $pipeline
$frequencias = @("horaria")
if ((Get-Date).Hour -eq 6) { $frequencias += "diaria" }

$falhou = $false
foreach ($frequencia in $frequencias) {
    Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') iniciando $frequencia"
    & $python $script --frequencia $frequencia --armazenamento mongo --padronizada neon *>> $log
    if ($LASTEXITCODE -ne 0) { $falhou = $true }
    Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') fim de $frequencia, código $LASTEXITCODE"
}
if ($falhou) { exit 1 }
