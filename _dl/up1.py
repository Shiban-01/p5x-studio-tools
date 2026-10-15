"""Prueba 1: UnityPy lee y lista tipos del bundle de animaciones."""
import sys
import UnityPy

p = r"C:/Users/Lukas/p5x-datamining/_dl/test_anim/anim_playable14d1c564.bundle"
env = UnityPy.load(p)
objs = list(env.objects)
print("objetos:", len(objs))
from collections import Counter
print(Counter(o.type.name for o in objs))
clips = [o for o in objs if o.type.name == "AnimationClip"]
print("clips:", len(clips), [o.name for o in clips[:5]])
