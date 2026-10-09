"""Number trivia for the Mathematics category, worked out here rather than looked up, so every
answer is right by construction. Many kinds of question (Roman numerals, polygons, primes,
powers, percentages, number words, sequences, binary…), each with its own phrasings, and
wrong answers that are the mistakes people actually make (an off-by-one, the neighbouring
square, the wrong polygon)."""

import math

from common import make_question, new_rng, pick

POLYGONS = {3: "triangle", 4: "quadrilateral", 5: "pentagon", 6: "hexagon", 7: "heptagon", 8: "octagon",
            9: "nonagon", 10: "decagon", 11: "hendecagon", 12: "dodecagon", 20: "icosagon"}
ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
         (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
LARGE_NUMBERS = {"thousand": 3, "million": 6, "billion": 9, "trillion": 12, "quadrillion": 15}


def roman(n):
    out = ""
    for value, symbol in ROMAN:
        while n >= value:
            out, n = out + symbol, n - value
    return out


def is_prime(n):
    return n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))


def near_numbers(answer, rng, spread, minimum=0, avoid=()):
    """Three wrong numbers near the answer, never one the question itself shows (`avoid`)."""
    picks = set()
    while len(picks) < 3:
        guess = answer + rng.choice([-1, 1]) * rng.choice(spread)
        if guess != answer and guess >= minimum and guess not in avoid:
            picks.add(guess)
    return [str(p) for p in sorted(picks)]


def question(question_text, answer, wrong, difficulty, kind="multiple", key=None):
    q = make_question(19, question_text, answer, wrong, difficulty=difficulty, source="generated", kind=kind)
    q["_item"], q["_fame"] = key or question_text, 0
    return q


def generate():
    rng, out = new_rng("mathematics"), []

    # Roman numerals, both ways (years read on buildings and film credits are the classic)
    for n in rng.sample(range(1, 3000), 160):
        r, level = roman(n), "easy" if n < 50 else "medium" if n < 1000 else "hard"
        out.append(question(pick(rng, f"What number is written {r} in Roman numerals?", f"Convert the Roman numeral {r} to an ordinary number.",
                                 f"A cornerstone is carved with {r}. Which number is that?"),
                            str(n), near_numbers(n, rng, (1, 2, 4, 5, 9, 10, 40, 50, 100), 1), level, key=f"roman-{n}"))
    for n in rng.sample(range(1900, 2030), 40):
        wrong = sorted({roman(n + d) for d in rng.sample([-10, -9, -4, -1, 1, 4, 9, 10, 40], 3)})
        out.append(question(pick(rng, f"How is the year {n} written in Roman numerals?", f"Which Roman numeral stands for {n}?"),
                            roman(n), wrong, "medium", key=f"roman-year-{n}"))

    # Polygons: sides, interior angles, and their sum
    for sides, name in POLYGONS.items():
        others = [str(s) for s in rng.sample([s for s in POLYGONS if s != sides], 3)]
        out.append(question(pick(rng, f"How many sides does a {name} have?", f"A {name} has how many sides?"),
                            str(sides), others, "easy" if sides <= 8 else "medium", key=f"poly-{sides}"))
        total = (sides - 2) * 180
        out.append(question(f"What do the interior angles of a {name} add up to, in degrees?", str(total),
                            [str(total + d) for d in rng.sample([-360, -180, 180, 360, 90], 3)], "medium" if sides <= 6 else "hard",
                            key=f"poly-sum-{sides}"))
        if 360 % sides == 0 or sides in (5, 8, 10, 12):
            angle = total / sides
            shown = f"{angle:g}"
            wrong = sorted({f"{(t - 2) * 180 / t:g}" for t in POLYGONS if t != sides and ((t - 2) * 180 / t) % 1 == 0})
            out.append(question(f"Each interior angle of a regular {name} measures how many degrees?", shown,
                                rng.sample([w for w in wrong if w != shown], 3), "hard", key=f"poly-angle-{sides}"))
        names = [n for s, n in POLYGONS.items() if s != sides]
        out.append(question(pick(rng, f"What do you call a polygon with {sides} sides?", f"A flat shape with exactly {sides} straight sides is a…"),
                            name.capitalize(), [n.capitalize() for n in rng.sample(names, 3)], "easy" if sides <= 8 else "medium",
                            key=f"poly-name-{sides}"))

    # Primes
    for _ in range(90):
        prime = rng.choice([p for p in range(11, 400) if is_prime(p)])
        composites = rng.sample([c for c in range(prime - 30, prime + 30) if c > 3 and not is_prime(c) and c % 2], 3)
        out.append(question(pick(rng, "Which of these numbers is prime?", "Only one of these is a prime number. Which?"),
                            str(prime), [str(c) for c in composites], "easy" if prime < 60 else "medium" if prime < 150 else "hard",
                            key=f"prime-{prime}"))
    for p in [p for p in range(2, 200) if is_prime(p)][:40]:
        nxt = next(q for q in range(p + 1, 400) if is_prime(q))
        out.append(question(f"What is the next prime number after {p}?", str(nxt),
                            near_numbers(nxt, rng, (1, 2, 3, 4), avoid={p}), "easy" if p < 30 else "medium", key=f"next-prime-{p}"))

    # Powers, roots and factorials
    for n in range(4, 31):
        out.append(question(pick(rng, f"What is the square root of {n * n}?", f"Which number multiplied by itself gives {n * n}?"),
                            str(n), near_numbers(n, rng, (1, 2, 3)), "easy" if n <= 12 else "medium", key=f"root-{n}"))
        out.append(question(f"What is {n} squared?", str(n * n), [str((n + d) ** 2) if d else str(n * n + n) for d in rng.sample([-1, 1, 0], 3)],
                            "easy" if n <= 12 else "medium", key=f"square-{n}"))
    for n in range(2, 11):
        out.append(question(f"What is {n} cubed?", str(n ** 3), [str((n + d) ** 3) for d in (-1, 1)] + [str(n ** 2 * 3)],
                            "easy" if n <= 4 else "medium", key=f"cube-{n}"))
    for n in range(3, 11):
        out.append(question(pick(rng, f"What is {n}! ({n} factorial)?", f"{n} factorial ({n}!) equals what?"),
                            str(math.factorial(n)), [str(math.factorial(n - 1)), str(math.factorial(n + 1)), str(math.factorial(n) // 2)],
                            "medium" if n <= 6 else "hard", key=f"fact-{n}"))
    for exp in range(5, 16):
        out.append(question(f"What is 2 to the power of {exp}?", str(2 ** exp), [str(2 ** (exp - 1)), str(2 ** (exp + 1)), str(2 ** exp + 2 ** (exp - 2))],
                            "easy" if exp <= 8 else "medium" if exp <= 11 else "hard", key=f"pow2-{exp}"))

    # Percentages and fractions of amounts
    for _ in range(80):
        percent, amount = rng.choice([5, 10, 12.5, 15, 20, 25, 30, 40, 50, 60, 75, 80, 150]), rng.choice(range(20, 801, 20))
        answer = percent * amount / 100
        if answer != int(answer):
            continue
        answer = int(answer)
        out.append(question(pick(rng, f"What is {percent:g}% of {amount}?", f"Take {percent:g}% of {amount}. What do you get?"),
                            str(answer), near_numbers(answer, rng, (2, 5, 10, 20, 25), 1), "easy" if percent in (10, 25, 50) else "medium",
                            key=f"pct-{percent}-{amount}"))

    # Number words and the size of large numbers
    for word, zeros in LARGE_NUMBERS.items():
        out.append(question(pick(rng, f"How many zeros are there in one {word}?", f"Written out in full, one {word} has how many zeros?"),
                            str(zeros), [str(z) for z in rng.sample([z for z in range(2, 19) if z != zeros], 3)],
                            "easy" if zeros <= 6 else "medium", key=f"zeros-{word}"))
    for name, value in [("a dozen", 12), ("a baker's dozen", 13), ("a score", 20), ("a gross", 144), ("a great gross", 1728)]:
        out.append(question(f"How many is {name}?", str(value), near_numbers(value, rng, (1, 2, 8, 12), 2),
                            "easy" if value < 20 else "medium" if value < 200 else "hard", key=f"word-{name}"))

    # Binary and other bases
    for n in rng.sample(range(5, 64), 30):
        b = bin(n)[2:]
        out.append(question(pick(rng, f"What is the binary number {b} in ordinary (decimal) numbers?", f"Convert {b} from binary to decimal."),
                            str(n), near_numbers(n, rng, (1, 2, 4, 8)), "medium" if n < 16 else "hard", key=f"bin-{n}"))
    for n in rng.sample(range(16, 256), 15):
        out.append(question(f"What is the hexadecimal number {n:X} in decimal?", str(n), near_numbers(n, rng, (1, 6, 10, 16)), "hard",
                            key=f"hex-{n}"))

    # Sequences
    fib = [1, 1]
    while len(fib) < 20:
        fib.append(fib[-1] + fib[-2])
    for start in range(2, 14):
        shown = ", ".join(str(x) for x in fib[start - 2:start + 3])
        nxt = fib[start + 3]
        out.append(question(pick(rng, f"What comes next in the Fibonacci sequence: {shown}, …?", f"Continue the sequence {shown}, …"),
                            str(nxt), near_numbers(nxt, rng, (1, 2, 3, fib[start + 1] // 2 or 1), avoid=set(fib[start - 2:start + 3])), "easy" if start < 6 else "medium",
                            key=f"fib-{start}"))
    for _ in range(30):
        first, step = rng.randint(1, 20), rng.randint(2, 12)
        terms = [first + step * i for i in range(5)]
        nxt = first + step * 5
        out.append(question(f"What comes next: {', '.join(map(str, terms))}, …?", str(nxt), near_numbers(nxt, rng, (1, 2, step // 2 or 1, step), avoid=set(terms)),
                            "easy", key=f"arith-{first}-{step}"))
    for ratio in (2, 3, 4, 5):
        terms = [ratio ** i for i in range(1, 5)]
        nxt = ratio ** 5
        out.append(question(f"What comes next: {', '.join(map(str, terms))}, …?", str(nxt),
                            [str(nxt - ratio), str(terms[-1] * 2 + ratio), str(nxt + ratio ** 2)], "medium", key=f"geo-{ratio}"))

    # A few true-or-false facts about numbers
    facts = [("Zero is an even number.", True), ("1 is a prime number.", False), ("2 is the only even prime number.", True),
             ("Pi is exactly 22/7.", False), ("The square root of 2 is an irrational number.", True),
             ("A triangle can have two right angles.", False), ("Every square is a rectangle.", True),
             ("Every rectangle is a square.", False), ("0.999… recurring is equal to 1.", True),
             ("There are more prime numbers between 1 and 100 than between 101 and 200.", True),
             ("The angles in a triangle always add up to 180 degrees on a flat surface.", True),
             ("A circle has exactly one line of symmetry.", False), ("Negative numbers have no square roots among the real numbers.", True),
             ("The number 1,000,000 has seven digits.", True), ("Every prime number greater than 2 is odd.", True)]
    for statement, truth in facts:
        out.append(question(statement, "True" if truth else "False", None, "medium", kind="boolean", key=statement))

    # Famous constants, to a few decimal places
    for name, value, decimals in [("pi", math.pi, 2), ("pi", math.pi, 4), ("e (Euler's number)", math.e, 2), ("the golden ratio", (1 + 5 ** 0.5) / 2, 3),
                                  ("the square root of 2", 2 ** 0.5, 3)]:
        right = f"{value:.{decimals}f}"
        step = 10 ** -decimals
        wrong = [f"{value + d * step:.{decimals}f}" for d in (-3, 2, 5)]
        out.append(question(f"To {decimals} decimal places, what is {name}?", right, wrong, "easy" if decimals == 2 and name == "pi" else "hard",
                            key=f"const-{name}-{decimals}"))
    return out
