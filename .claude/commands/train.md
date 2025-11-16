---
description: Train the system with random variations of a base prompt until a key is pressed
---

You are a training orchestrator for the DSE (Digital Synthetic Evolution) system.

The user wants to run continuous training by executing random variations of a base prompt.

Steps to follow:
1. Parse the user's base prompt from the /train command arguments
2. If no prompt provided, use random factory tasks as default
3. Launch the factory task trainer script with the base prompt
4. The script will:
   - Generate random variations of the base prompt
   - Execute each variation through the DSE workflow system
   - Track performance metrics and success rates
   - Continue until the user presses a key
   - Display statistics when stopped

Execute the training with:
```bash
python code_evolver/factory_task_trainer.py --prompt "<base_prompt>"
```

If the user just typed `/train` with no arguments, use:
```bash
python code_evolver/factory_task_trainer.py
```

The script will run continuously and can be stopped by pressing any key in the console.
