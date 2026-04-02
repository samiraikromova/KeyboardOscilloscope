import numpy as np
import sounddevice as sd
import pygame
import threading

RATE      = 44100
CHUNK     = 1024
AMPLITUDE = 0.18

# per-key phase — each note tracks its own position in the sine cycle
# without this, holding a chord causes phase jumps = clicks
phases = {}
phases_lock = threading.Lock()

active = set()
notes_lock = threading.Lock()

# full keyboard layout — 3 rows, 3 octaves
# z-row: C3 (low/bass), a-row: C4 (middle), q-row: C5 (high)
KEY_FREQS = {
    # z row — bass octave (C3)
    pygame.K_z: (130.81, "C3"), pygame.K_x: (146.83, "D3"),
    pygame.K_c: (164.81, "E3"), pygame.K_v: (174.61, "F3"),
    pygame.K_b: (196.00, "G3"), pygame.K_n: (220.00, "A3"),
    pygame.K_m: (246.94, "B3"),

    # a row — middle octave (C4)
    pygame.K_a: (261.63, "C4"), pygame.K_s: (293.66, "D4"),
    pygame.K_d: (329.63, "E4"), pygame.K_f: (349.23, "F4"),
    pygame.K_g: (392.00, "G4"), pygame.K_h: (440.00, "A4"),
    pygame.K_j: (493.88, "B4"), pygame.K_k: (523.25, "C5"),

    # q row — high octave (C5-C6)
    pygame.K_q: (523.25, "C5"), pygame.K_w: (587.33, "D5"),
    pygame.K_e: (659.25, "E5"), pygame.K_r: (698.46, "F5"),
    pygame.K_t: (783.99, "G5"), pygame.K_y: (880.00, "A5"),
    pygame.K_u: (987.77, "B5"), pygame.K_i: (1046.50, "C6"),

    # number row — chords shortcut (common intervals)
    pygame.K_1: (261.63, "C4"), pygame.K_2: (329.63, "E4"),
    pygame.K_3: (392.00, "G4"), pygame.K_4: (440.00, "A4"),
    pygame.K_5: (493.88, "B4"), pygame.K_6: (523.25, "C5"),
}


def audio_callback(outdata, frames, time_info, status):
    mixed = np.zeros(frames, dtype=np.float64)

    with notes_lock:
        keys = list(active)

    with phases_lock:
        for key in keys:
            freq = KEY_FREQS[key][0]

            # init phase for newly pressed key
            if key not in phases:
                phases[key] = 0.0

            p    = phases[key]
            step = 2 * np.pi * freq / RATE
            t    = np.arange(frames) * step + p
            mixed += np.sin(t)

            # save end phase — next buffer starts exactly where this one ends
            phases[key] = (p + frames * step) % (2 * np.pi)

        # clean up phases for released keys
        for key in list(phases):
            if key not in keys:
                del phases[key]

    if keys:
        # divide by note count keeps volume flat regardless of chord size
        mixed = (mixed / len(keys)) * AMPLITUDE

    # soft clip instead of hard clip — sounds warmer at high volumes
    mixed = np.tanh(mixed * 2) * 0.5

    outdata[:, 0] = mixed.astype(np.float32)


stream = sd.OutputStream(
    samplerate=RATE, blocksize=CHUNK,
    channels=1, dtype='float32',
    callback=audio_callback
)
stream.start()

# --- pygame ---
pygame.init()
W, H = 1150, 580
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("KeyboardOscilloscope  —  Day 07")
pg_clock = pygame.time.Clock()

MONO   = pygame.font.SysFont('monospace', 13)
MONO_B = pygame.font.SysFont('monospace', 14, bold=True)

BG       = (8,  8, 12)
GRIDC    = (22, 22, 35)
ZEROC    = (45, 45, 65)
SUMC     = (255, 255, 255)
DIMC     = (55, 55, 75)

# each active note gets one of these
PALETTE = [
    (0,   210, 130),  # teal
    (80,  160, 255),  # blue
    (255, 100,  80),  # red
    (255, 200,  50),  # yellow
    (180, 100, 255),  # purple
    (50,  220, 220),  # cyan
    (255, 140,   0),  # orange
    (190, 255,  90),  # lime
]

PLOT_X = 20
PLOT_Y = 55
PLOT_W = W - 40
PLOT_H = H - 175   # leaves room for keyboard strip at bottom
N_PTS  = PLOT_W    # one pixel per sample point


def build_display_wave(freq, n):
    # use actual frequency ratio so wave shape reflects the real pitch
    # base = C3 (130.81Hz), higher notes show more cycles
    cycles = max(1, round(freq / 130.81))
    t = np.linspace(0, cycles * 2 * np.pi, n, endpoint=False)
    return np.sin(t)


def wave_to_screen(wave, mid_y, half_h, color, width=1):
    scale = half_h * 0.88
    pts = [
        (PLOT_X + i, int(mid_y - wave[i] * scale))
        for i in range(len(wave))
    ]
    if len(pts) > 1:
        pygame.draw.lines(screen, color, False, pts, width)


def draw_grid():
    mid = PLOT_Y + PLOT_H // 2
    # center zero line
    pygame.draw.line(screen, ZEROC, (PLOT_X, mid), (PLOT_X + PLOT_W, mid), 1)
    # amplitude guide lines at ±25%, ±50%, ±75%
    for frac in (0.25, 0.5, 0.75):
        off = int(PLOT_H * 0.5 * frac)
        for sign in (-1, 1):
            y = mid + sign * off
            pygame.draw.line(screen, GRIDC, (PLOT_X, y), (PLOT_X + PLOT_W, y), 1)
    # border
    pygame.draw.rect(screen, GRIDC, (PLOT_X, PLOT_Y, PLOT_W, PLOT_H), 1)


def draw_keyboard(keys_down):
    # visual keyboard strip at the bottom showing all mapped keys
    rows = [
        ([pygame.K_q,pygame.K_w,pygame.K_e,pygame.K_r,pygame.K_t,
          pygame.K_y,pygame.K_u,pygame.K_i], "C5–C6"),
        ([pygame.K_a,pygame.K_s,pygame.K_d,pygame.K_f,pygame.K_g,
          pygame.K_h,pygame.K_j,pygame.K_k], "C4–C5"),
        ([pygame.K_z,pygame.K_x,pygame.K_c,pygame.K_v,pygame.K_b,
          pygame.K_n,pygame.K_m],            "C3–B3"),
    ]
    kw, kh, gap = 44, 34, 3
    y0 = PLOT_Y + PLOT_H + 18

    for row_i, (row_keys, row_label) in enumerate(rows):
        lbl = MONO.render(row_label, True, (55, 55, 80))
        screen.blit(lbl, (PLOT_X, y0 + row_i * (kh + gap) + 10))
        for col_i, pkey in enumerate(row_keys):
            x = PLOT_X + 75 + col_i * (kw + gap)
            y = y0 + row_i * (kh + gap)
            active_here = pkey in keys_down
            color_idx   = sorted(keys_down).index(pkey) if active_here else -1
            fill = PALETTE[color_idx % len(PALETTE)] if active_here else (22, 22, 35)
            pygame.draw.rect(screen, fill, (x, y, kw, kh), border_radius=5)
            pygame.draw.rect(screen, (55, 55, 75), (x, y, kw, kh), 1, border_radius=5)
            _, note = KEY_FREQS[pkey]
            k_txt = MONO_B.render(pygame.key.name(pkey).upper(), True,
                                  (255,255,255) if active_here else (60,60,85))
            n_txt = MONO.render(note, True,
                                (220,220,220) if active_here else (45,45,68))
            screen.blit(k_txt, (x + kw//2 - k_txt.get_width()//2, y + 4))
            screen.blit(n_txt, (x + kw//2 - n_txt.get_width()//2, y + 18))


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key in KEY_FREQS:
                with notes_lock:
                    active.add(event.key)
        elif event.type == pygame.KEYUP:
            if event.key in KEY_FREQS:
                with notes_lock:
                    active.discard(event.key)

    screen.fill(BG)
    draw_grid()

    with notes_lock:
        keys_snap = sorted(active)

    mid  = PLOT_Y + PLOT_H // 2
    half = PLOT_H // 2

    if not keys_snap:
        msg = MONO.render("press keys to play  —  z/x/c=bass  a/s/d=mid  q/w/e=high", True, DIMC)
        screen.blit(msg, (PLOT_X + PLOT_W//2 - msg.get_width()//2, mid - 7))
    else:
        # draw individual waves faintly — each at reduced scale so they don't crowd
        combined = np.zeros(N_PTS)
        for i, key in enumerate(keys_snap):
            freq, note = KEY_FREQS[key]
            w     = build_display_wave(freq, N_PTS)
            combined += w
            color = PALETTE[i % len(PALETTE)]
            # individual waves at 28% height so superposition stands out
            wave_to_screen(w, mid, half * 0.28, (*color, 160), width=1)

            # legend on the right
            leg = MONO.render(f"{note}  {freq:.0f}Hz", True, color)
            screen.blit(leg, (PLOT_X + PLOT_W - 115, PLOT_Y + 6 + i * 17))

        # normalize and draw the superposition full-height in white
        mx = np.max(np.abs(combined)) or 1
        wave_to_screen(combined / mx, mid, half * 0.88, SUMC, width=2)

        # label for the sum wave
        sum_lbl = MONO_B.render(f"sum  ({len(keys_snap)} waves)", True, SUMC)
        screen.blit(sum_lbl, (PLOT_X + PLOT_W - 115,
                               PLOT_Y + 6 + len(keys_snap) * 17 + 8))

    # title + chord info
    title = MONO_B.render("KeyboardOscilloscope", True, (90, 90, 120))
    screen.blit(title, (PLOT_X, 18))
    if keys_snap:
        chord = "  +  ".join(KEY_FREQS[k][1] for k in keys_snap)
        c_lbl = MONO_B.render(chord, True, (120, 200, 140))
        screen.blit(c_lbl, (PLOT_X + 200, 18))

    draw_keyboard(set(keys_snap))

    pygame.display.flip()
    pg_clock.tick(60)

stream.stop()
stream.close()
pygame.quit()