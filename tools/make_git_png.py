# -*- coding: utf-8 -*-
"""Рендерит историю коммитов и список веток в PNG для отчёта по лабе №2."""
import os
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def render(text, title, path, font=11):
    lines = text.rstrip("\n").splitlines()
    h = max(3, 0.45 * len(lines) + 1.2)
    fig, ax = plt.subplots(figsize=(11, h))
    ax.axis("off")
    ax.text(0.5, 1.0, title, fontsize=14, weight="bold", ha="right", va="top",
            transform=ax.transAxes)
    ax.text(0.01, 0.97, text, fontsize=font, family="Consolas", va="top",
            transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#f8fafc", edgecolor="#cbd5e1"))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("OK:", os.path.relpath(path, ROOT))


render(git("log", "--graph", "--oneline", "--all", "--decorate"),
       "История коммитов (git log --graph --oneline --all)",
       os.path.join(OUT, "git_history.png"))

branches = git("branch", "-a") + "\n" + git("log", "-1", "--format=Последний коммит: %h %s (%ci)")
render(branches, "Ветки репозитория (git branch -a)",
       os.path.join(OUT, "git_branches.png"))
