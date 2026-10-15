import tkinter as tk
from tkinter import ttk
root = tk.Tk()
root.geometry("300x200")
c = ttk.Combobox(root, values=["a","b","c"], state="readonly")
c.pack()
events = []
c.bind("<<ComboboxSelected>>", lambda e: events.append("sel"))
root.update()
c.current(1)
root.update()
print("after current(1):", events, "current=", c.current())
c.set("c")
root.update()
print("after set(c):", events, "current=", c.current())
root.destroy()