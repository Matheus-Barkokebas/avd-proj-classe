# `agendamento/` — coleta do COP de hora em hora

O servidor do COP não responde às máquinas do GitHub, que ficam nos EUA. Por isso a coleta roda numa máquina no Brasil e
**só acontece com ela ligada**. Para coletar 24 horas por dia, é preciso um servidor no Brasil.

Antes de agendar, a `pipeline/` precisa ter o `.venv` com as dependências e o `.env` preenchido.

Rode no PowerShell, de dentro de `pipeline/`, para criar a tarefa:

```powershell
schtasks /Create /SC HOURLY /MO 1 /TN "AerVita Coleta COP" /ST 00:10 /TR "powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $PWD\agendamento\coleta_horaria.ps1"
```

Para testar sem esperar a próxima hora:

```powershell
schtasks /Run /TN "AerVita Coleta COP"
```

Para remover:

```powershell
schtasks /Delete /TN "AerVita Coleta COP" /F
```

O registro de cada coleta fica em `data/coleta_horaria.log`, que não vai para o Git.
