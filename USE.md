# Spatial Description Contract

## Why this exists
Phrases like "a bit to the left" or "tilt it back" make sense between two people standing in the same room, because you both know where "left" and "back" are. They stop working once you're describing an object to an AI — there's no shared room, no shared "left." This guide gives you a fixed, simple way to describe position and tilt so it comes out right every time.

## Step 1: Set up your imaginary viewpoint
Picture yourself standing still, facing **North**, with the object placed on a table in front of you. This is your fixed viewpoint for the whole conversation — you never turn around, and the object doesn't either, unless you rotate it on purpose.

From this position:
- **North** = straight ahead of you
- **South** = behind you
- **East** = to your right
- **West** = to your left
- **Up** = toward the ceiling
- **Down** = toward the floor

Keep this setup for the whole project. Don't re-imagine yourself standing somewhere else halfway through — that's what causes confusion.

## Step 2: Describing where something goes
Instead of "near the corner" or "a bit to the side," say **which named part** you're measuring from, **which direction**, and **how far**.

- ❌ "Put the hole near the top corner"
- ✅ "50mm North and 20mm East of the center of the top face"

Always name the starting point (a face, a corner, a hole) — words like "here" or "there" don't carry any real information.

## Step 3: Describing a tilt
Three simple words cover every tilt or turn:

| Word | What it does |
|---|---|
| **Turn** (yaw) | Spins the object flat, like turning a steering wheel — around the Up/Down line |
| **Tilt** (pitch) | Rocks the object toward you or away from you — around the left-right (East-West) line |
| **Roll** | Rocks the object sideways, like rolling a barrel — around the North-South line |

For "Tilt," saying **"tilt toward me, n degrees"** is precise and reliable — it always means the top of the object leans toward you. "Tilt away from me, n degrees" is the opposite.

For "Turn," think of it like a clock face viewed from above: **"turn clockwise, n degrees"** or **"turn counterclockwise, n degrees"** both work fine, since looking down from above is a natural, unambiguous viewpoint.

"Roll" is the least intuitive — where possible, say **"roll toward my left"** or **"roll toward my right"** rather than clockwise/counterclockwise, since there's no natural viewing direction for it.

## When a part has its own smaller part attached
If you're describing a small piece that sits on a bigger piece (like a bracket on a frame), say clearly whether you mean directions from your own fixed viewpoint, or directions relative to the bracket itself — especially if the bracket has already been rotated. When in doubt, just say "from my viewpoint" to be safe.

## When words aren't enough
Some things are genuinely hard to describe in words alone:
- Curvy, rounded shapes with no flat side to measure from
- Several tilts/turns done one after another, where the order matters
- Vague sizing like "a bit bigger" — always better to give an actual number

In these cases, it's fine to present a sketch or a rough drawing instead of struggling to describe it in words.
