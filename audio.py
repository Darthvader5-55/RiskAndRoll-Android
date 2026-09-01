"""
game/audio.py
-------------
Sound, written so it can NEVER crash the game.

Two rules from the design document:
  * missing sound files must not stop the game
  * the booth may be running on a laptop with no working audio at all

So every single call in here is wrapped. If the mixer refuses to start, the
whole module quietly switches itself off and the game runs in silence.

WHERE THE SOUNDS COME FROM
The assets/sounds/ folder starts empty, so the game generates its own sounds
in memory at startup using plain Python maths. Drop a real .wav file into
assets/sounds/ with the matching name and it is used instead, no code change.

THE DICE CLACKS
A rolling sound is not one long noise file. Every clack you hear is a real
event: a die actually touching the floor or a wall in the physics. The volume
comes from how hard it landed and the pitch is picked at random from four
variants, so six dice coming down sounds like six dice and never like a loop.
That is why the rattle always matches what you can see.

A clack is short filtered NOISE, not a tone. Plastic hitting wood has no
musical pitch to it, and a beep here would sound like a video game from 1978.
"""

import math
import os
import struct

import pygame

from config import settings

SAMPLE_RATE = 22050

# name -> (filename it will look for, how to build it if the file is missing)
SOUND_FILES = {
    "click": "click.wav",
    "place": "place.wav",
    "beep": "beep.wav",
    "bounce": "bounce.wav",
    "win": "win.wav",
    "lose": "lose.wav",
    "jackpot": "jackpot.wav",
    "tick": "tick.wav",
    "clack1": "clack1.wav",
    "clack2": "clack2.wav",
    "clack3": "clack3.wav",
    "clack4": "clack4.wav",
    "settle": "settle.wav",
    "rumble": "rumble.wav",     # looped while the dice are tumbling
}

# how many clacks may overlap. Six dice landing together would otherwise
# stack into one loud mush and swallow every other sound.
MAX_CLACKS_PER_FRAME = 3


class Audio:
    """One of these is created by the GameManager and shared by every screen."""

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self._rumble_channel = None
        self.sfx_volume = settings.SFX_VOLUME
        self.music_volume = settings.MUSIC_VOLUME
        self.muted = not settings.AUDIO_ENABLED
        self._clacks_this_frame = 0
        self.rate, self.sample_size, self.channels = SAMPLE_RATE, -16, 1

        if not settings.AUDIO_ENABLED:
            return

        try:
            # pygame.init() may already have opened the mixer with its own
            # settings. Close it first, or our generated samples would be
            # played back at the wrong speed and in the wrong channel count.
            pygame.mixer.quit()
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1,
                              buffer=512)
            self.enabled = True
        except pygame.error:
            self.enabled = False      # no sound card, no problem
            return

        # Ask the mixer what it ACTUALLY gave us. It is allowed to ignore our
        # request, and generated sound has to match reality, not the request.
        init = pygame.mixer.get_init()
        if init:
            self.rate, self.sample_size, self.channels = init
        else:
            self.rate, self.sample_size, self.channels = SAMPLE_RATE, -16, 1

        self._load_all()

    # ==================================================================== load
    def _load_all(self):
        for name, filename in SOUND_FILES.items():
            path = os.path.join(settings.SOUND_DIR, filename)
            sound = None

            if os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                except pygame.error:
                    sound = None      # corrupt file: fall through to the beep

            if sound is None:
                sound = self._build_sound(name)

            if sound is not None:
                self.sounds[name] = sound

    # ================================================================ building
    def _build_sound(self, name):
        """Make a small arcade beep in memory, with no asset file needed."""
        if abs(self.sample_size) != 16:
            return None      # unusual mixer format: stay silent rather than screech

        fmt = (self.rate, self.channels)
        try:
            if name == "click":
                samples = _tone(880, 0.05, fmt, volume=0.25, shape="square")
            elif name == "place":
                samples = (_tone(520, 0.09, fmt, volume=0.30)
                           + _tone(780, 0.09, fmt, volume=0.30))
            elif name == "beep":
                samples = _tone(660, 0.12, fmt, volume=0.30, shape="square")
            elif name == "bounce":
                samples = _sweep(420, 180, 0.07, fmt, volume=0.22)
            elif name == "win":
                samples = (_tone(523, 0.10, fmt, volume=0.30)
                           + _tone(659, 0.10, fmt, volume=0.30)
                           + _tone(784, 0.18, fmt, volume=0.32))
            elif name == "lose":
                samples = _sweep(392, 160, 0.32, fmt, volume=0.28, shape="square")
            elif name == "jackpot":
                samples = (_tone(523, 0.09, fmt, volume=0.30)
                           + _tone(659, 0.09, fmt, volume=0.30)
                           + _tone(784, 0.09, fmt, volume=0.32)
                           + _tone(1047, 0.26, fmt, volume=0.34))
            elif name == "tick":
                samples = _tone(1200, 0.035, fmt, volume=0.18, shape="square")
            elif name == "rumble":
                # the tumbler itself: low, rough and loopable. The clacks sit
                # on top of this, so a roll has both a body and its impacts.
                samples = _noise(0.55, fmt, volume=0.30, low_hz=70, high_hz=240)
            elif name == "settle":
                samples = _knock(150, 0.13, fmt, volume=0.26)
            elif name.startswith("clack"):
                # four slightly different knocks, so repeated dice hits never
                # sound like the same sample played twice
                pitch = {"clack1": 340, "clack2": 420,
                         "clack3": 500, "clack4": 610}[name]
                samples = _knock(pitch, 0.055, fmt, volume=0.30)
            else:
                return None
            return pygame.mixer.Sound(buffer=samples)
        except (pygame.error, ValueError):
            return None

    # ==================================================================== play
    def play(self, name):
        """Play a sound by name. Unknown names are ignored on purpose."""
        if not self.enabled or self.muted:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            sound.set_volume(self.sfx_volume)
            sound.play()
        except pygame.error:
            pass

    def play_clack(self, strength=0.6):
        """One die touching something. strength is 0..1, from the physics.

        Called straight from the roll, so the sound and the picture cannot
        drift apart: no clack is ever played for a bounce that did not happen.
        """
        if not self.enabled or self.muted:
            return
        if self._clacks_this_frame >= MAX_CLACKS_PER_FRAME:
            return

        import random
        strength = max(0.0, min(1.0, strength))
        if strength < 0.06:
            return                      # too soft to hear anyway

        sound = self.sounds.get("clack%d" % random.randint(1, 4))
        if sound is None:
            return
        try:
            # a hard landing is louder; a gentle one is barely there
            sound.set_volume(self.sfx_volume * (0.25 + 0.75 * strength))
            sound.play()
            self._clacks_this_frame += 1
        except pygame.error:
            pass

    # ================================================================= rumble
    def start_rumble(self):
        """Begin the looping tumbler noise. Safe to call every frame."""
        if not self.enabled or self.muted:
            return
        if self._rumble_channel is not None and self._rumble_channel.get_busy():
            return
        sound = self.sounds.get("rumble")
        if sound is None:
            return
        try:
            self._rumble_channel = sound.play(loops=-1)
            if self._rumble_channel:
                self._rumble_channel.set_volume(0.0)
        except pygame.error:
            self._rumble_channel = None

    def set_rumble_level(self, level):
        """How loud the rumble is right now, 0..1.

        The screen feeds in how much the dice are still moving, so the noise
        dies away as they settle instead of stopping dead.
        """
        if self._rumble_channel is None:
            return
        try:
            self._rumble_channel.set_volume(
                self.sfx_volume * 0.55 * max(0.0, min(1.0, level)))
        except pygame.error:
            pass

    def stop_rumble(self):
        if self._rumble_channel is None:
            return
        try:
            self._rumble_channel.fadeout(220)
        except pygame.error:
            pass
        self._rumble_channel = None

    def begin_frame(self):
        """Called once a frame so the clack limit starts again."""
        self._clacks_this_frame = 0

    def set_volume(self, value):
        self.sfx_volume = max(0.0, min(1.0, value))

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop_rumble()
        return self.muted


# ===========================================================================
# TINY SOUND GENERATOR
# ===========================================================================
# 16-bit mono samples packed into bytes. struct.pack turns a Python number
# into the raw bytes the sound card expects.

def _envelope(index, total):
    """Fade in fast, fade out slowly, so the beep has no nasty click."""
    attack = max(1, int(total * 0.05))
    if index < attack:
        return index / attack
    return max(0.0, 1.0 - (index - attack) / max(1, total - attack))


def _pack(value, channels):
    """One sample, repeated once per channel (mono data into a stereo mixer)."""
    clamped = max(-32768, min(32767, int(value)))
    return struct.pack("<h", clamped) * channels


def _noise(seconds, fmt, volume=0.3, low_hz=70, high_hz=240):
    """Rough, low rumbling noise, built to loop without an obvious seam.

    Real noise is random, but a random buffer clicks every time it loops
    because the end does not match the start. Stacking a handful of quiet
    sine waves at awkward frequencies gives something noise-LIKE that joins
    up perfectly, which is what a looping sound needs.
    """
    import math
    rate, channels = fmt
    total = int(rate * seconds)
    voices = []
    for step in range(9):
        # frequencies spread across the band, deliberately not multiples of
        # each other, so they do not fuse into one musical note
        hz = low_hz + (high_hz - low_hz) * (step / 8.0) ** 1.4
        cycles = max(1, round(hz * seconds))          # whole cycles = seamless
        voices.append(cycles / seconds)

    data = bytearray()
    for index in range(total):
        t = index / rate
        value = sum(math.sin(2 * math.pi * hz * t) for hz in voices) / len(voices)
        # a slow wobble, so it breathes instead of humming flat
        value *= 0.75 + 0.25 * math.sin(2 * math.pi * (1.0 / seconds) * t)
        data += _pack(int(value * volume * 32767), channels)
    return bytes(data)


def _tone(frequency, seconds, fmt, volume=0.3, shape="sine"):
    rate, channels = fmt
    total = int(rate * seconds)
    data = bytearray()
    for i in range(total):
        wave = math.sin(2 * math.pi * frequency * (i / rate))
        if shape == "square":
            wave = 1.0 if wave >= 0 else -1.0
        data += _pack(wave * volume * _envelope(i, total) * 32767, channels)
    return bytes(data)


def _sweep(start_hz, end_hz, seconds, fmt, volume=0.3, shape="sine"):
    """A tone that slides from one pitch to another."""
    rate, channels = fmt
    total = int(rate * seconds)
    data = bytearray()
    phase = 0.0
    for i in range(total):
        frequency = start_hz + (end_hz - start_hz) * (i / max(1, total))
        phase += 2 * math.pi * frequency / rate
        wave = math.sin(phase)
        if shape == "square":
            wave = 1.0 if wave >= 0 else -1.0
        data += _pack(wave * volume * _envelope(i, total) * 32767, channels)
    return bytes(data)


def _knock(pitch, seconds, fmt, volume=0.3):
    """A short burst of filtered noise: plastic hitting a hard surface.

    Real dice have no musical note in them, so this starts as random noise,
    gets smoothed towards the given pitch (a cheap low-pass filter) and then
    drops away fast. It sounds like a knock rather than a beep.
    """
    import random
    rate, channels = fmt
    count = int(rate * seconds)
    data = bytearray()

    smoothing = max(0.0, min(0.95, 1.0 - pitch / float(rate) * 6.0))
    previous = 0.0

    for index in range(count):
        noise = random.uniform(-1.0, 1.0)
        # low-pass: mix each sample with the one before it
        previous = previous * smoothing + noise * (1.0 - smoothing)
        # a sharp attack then a fast fall away
        fade = (1.0 - index / count) ** 3.2
        value = int(previous * fade * volume * 32767)
        value = max(-32767, min(32767, value))
        packed = struct.pack("<h", value)
        data += packed * channels

    return bytes(data)
