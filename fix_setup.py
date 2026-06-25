import sys, re

with open('setup_wizard.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace _run_step_4 and 5
pattern = r'    # ═══════════════════════════════════════════════════════════════════════════\n    #  PASSO 4 – OLLAMA.*?(?=    # ═══════════════════════════════════════════════════════════════════════════\n    #  PASSO 6)'
code = re.sub(pattern, '', code, flags=re.DOTALL)

# Rename _run_step_6 to _run_step_4
code = code.replace('_run_step_6(self):', '_run_step_4(self):')
code = code.replace('self._run_step_6', 'self._run_step_4')
code = code.replace('self._run_step_5', 'self._run_step_3')
code = code.replace('PASSO 6', 'PASSO 4')

with open('setup_wizard.py', 'w', encoding='utf-8') as f:
    f.write(code)
