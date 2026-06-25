import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace start_processing validation
validation_code = """
        run_ocr = self.var_ocr.get()
        run_correct = self.var_correct.get()
        run_translate = self.var_translate.get()
        
        # Validação Modular
        if run_ocr and not self.check_module_ocr():
            self.log("⚠️ ATENÇÃO: O Motor OCR não está instalado.")
            self.log("Vá até a aba 'Central de Módulos' e instale-o antes de usar a Etapa 1.")
            self.tabview.set("Central de Módulos")
            return
            
        if (run_correct or run_translate) and not self.check_module_translation():
            self.log("⚠️ ATENÇÃO: O Motor de Tradução (IA) não está instalado.")
            self.log("Vá até a aba 'Central de Módulos' e instale-o antes de usar as Etapas 2 e 3.")
            self.tabview.set("Central de Módulos")
            return
"""

# We search for:
old_vars = """        run_ocr = self.var_ocr.get()
        run_correct = self.var_correct.get()
        run_translate = self.var_translate.get()"""

if old_vars in code:
    code = code.replace(old_vars, validation_code)
    
# Now fix action_process_queue
queue_validation_code = """
        run_ocr = self.var_ocr.get()
        run_correct = self.var_correct.get()
        run_translate = self.var_translate.get()
        
        # Validação Modular
        if run_ocr and not self.check_module_ocr():
            self.tabview.set("Central de Módulos")
            self.log("⚠️ ATENÇÃO: O Motor OCR não está instalado. Instale na Central de Módulos.")
            return
            
        if (run_correct or run_translate) and not self.check_module_translation():
            self.tabview.set("Central de Módulos")
            self.log("⚠️ ATENÇÃO: O Motor de Tradução não está instalado. Instale na Central de Módulos.")
            return
"""

old_vars_queue = """        out_path = self.entry_output.get().strip()
        run_ocr = self.var_ocr.get()
        run_correct = self.var_correct.get()
        run_translate = self.var_translate.get()"""

if old_vars_queue in code:
    code = code.replace(old_vars_queue, "        out_path = self.entry_output.get().strip()\n" + queue_validation_code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Validation injected.")
