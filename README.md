# power_tree_editor

Power Tree Editor

A graphical editor built with PySide6 to design and analyze power supply trees.
Each node represents a stage (source, LDO, DC/DC, load), and the tool automatically computes electrical parameters (efficiency, dissipation, errors, etc.).

✨ Features

🔌 Create nodes: INPUT, LDO, DCDC, LOAD

🔗 Visual connection between nodes (drag & drop)

⚡ Automatic calculation of:

Input / output voltages

Efficiency

Power dissipation and quiescent current (Iq)

Constraint checks (Vin min/max, Iout max, etc.)

📝 Property inspector to edit node parameters

🚨 Error panel to diagnose design issues

💾 Save / load schematics in JSON format

To run : python app.py

Dependancies: PySide6>=6.6

<img width="1919" height="798" alt="Screenshot_1" src="https://github.com/user-attachments/assets/f64d013e-f2a6-4669-b49b-d41589ce20c1" />
