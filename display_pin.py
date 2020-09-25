### display_pin.py v0.13
### A displayio object for showing the state and value of a pin

### Tested with an Adafruit CLUE and CircuitPython and 5.3.1

### MIT License

### Copyright (c) 2020 Kevin J. Walters

### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:

### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.

### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.


### TODO - apply restictions on font size based on width, e.g. height=36, width=120

import displayio
import terminalio

import adafruit_display_text.label


WRITE_COLOR = 0xe0e000
WRITE_COLOR_DIM = 0x909020

READ_COLOR = 0x00e0e0
READ_COLOR_DIM = 0x209090

TEXT_COLOR = 0xc0c0c0


class DisplayPin:

    _NAME_WIDTH = 3


    def __init__(self,
                 name, mode="unused", units="CP",
                 *,
                 value=None,
                 vref=3.3,
                 width=120, height=18, font=terminalio.FONT,
                 label_color=TEXT_COLOR,
                 bg_color=None,  ### pylint: disable=unused-argument
                 ):
        ### pylint: disable=too-many-locals
        self._name = name
        self._units = units

        self._mode = mode
        self._user_value = None  ### This is set at end using value property
        self._width = width
        self._height = height
        self._scale = None

        if self._units == "CP":
            value_range = 65536
        elif self._units == "MP":
            value_range = 1024
        else:
            ValueError("Unbelievable carelessness $USER: units must be CP or MP")

        self._dio_font = font
        font_bb = self._dio_font.get_bounding_box()
        ### 9//14 covers the height of capitals (no descenders)
        scale = height // (font_bb[1] * 9 // 14)
        self._name_dob = adafruit_display_text.label.Label(text=name[:self._NAME_WIDTH].upper(),
                                                           font=self._dio_font,
                                                           color=label_color,
                                                           scale=scale)
        self._name_dob.y = (height - 1) // 2  ### positioning assume upper case
        self._group = displayio.Group(max_size=3)
        self._group.append(self._name_dob)

        font_bb = self._dio_font.get_bounding_box()
        label_width = self._NAME_WIDTH * scale * font_bb[0]
        gap = 4
        data_width = width - label_width - gap
        self._data_dob_pos = label_width + gap

        if mode in ("read_analog", "write_trueanalog"):
            labels = height >= 60
            self._data = DisplayPinDataAnalog(data_width, height, mode=="write_trueanalog",
                                              vref=vref, value_range=value_range,
                                              labels=labels, font=self._dio_font)
            self._data.group.x = self._data_dob_pos

        elif mode in ("read_digital", "write_digital"):
            self._data = DisplayPinDataDigital(data_width, height, mode=="write_digital",
                                               vref=vref)
            self._data.group.x = self._data_dob_pos

        elif mode == "write_analog":  ### TODO - consider giving this an alias of "pwm"
            self._data = DisplayPinDataPWM(data_width, height,
                                           vref=vref, value_range=value_range)
            self._data.group.x = self._data_dob_pos

        elif mode == "touch":
            self._data = DisplayPinDataTouch(data_width, height)
            self._data.group.x = self._data_dob_pos

        elif mode == "music_frequency":
            self._data = DisplayPinDataMusic(data_width, height)
            self._data.group.x = self._data_dob_pos

        else:
            self._data = None

        if self._data:
            self._group.append(self._data.group)

        self.value = value


    @property
    def group(self):
        return self._group


    @property
    def value(self):
        return self._user_value

    @value.setter
    def value(self, data):
        self._user_value = data
        if self._data is not None:
            self._data.value = data


    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, new_mode):
        self._mode = new_mode
        ### TODO - change mode and probably None out the _data


class DisplayPinDataAnalog:
    """A lightweight bar graph."""

    _LINE_COL_IDX = 1
    _SCALE_COL_IDX = 2


    def _makeLine(self, width, height, col_idx):
        line = displayio.Bitmap(width, height, len(self._palette))
        line.fill(col_idx)
        tg = displayio.TileGrid(line, pixel_shader=self._palette)
        return tg


    def _makeScale(self, vref, tick_width, width, height, col_idx,
                   label_height=None, font=None):
        ### pylint: disable=too-many-locals,too-many-branches
        scale_height = height - label_height if label_height else height
        scale_line = displayio.Bitmap(width, scale_height, len(self._palette))
        scale_bottom_row = scale_height - 1
        tick_ratio = 5

        labels = []
        major_ticks = list(range(0, int(vref) + 1))
        if major_ticks[-1] != vref:
            major_ticks.append(vref)
        for idx, major_tick in enumerate(major_ticks):
            x_pos = int(major_tick / vref * self._scale_scfactor)

            ### Thicken first and last
            if idx == 0:
                x_range = range(tick_width + 1)
            elif idx == len(major_ticks) - 1:
                x_range = range(-1, tick_width)
            else:
                x_range = range(tick_width)
            for t_off_x in x_range:
                for t_row in range(scale_height):
                    scale_line[x_pos + t_off_x, t_row] = col_idx

            if label_height and major_tick == int(major_tick):
                lab = adafruit_display_text.label.Label(text=str(major_tick),
                                                        font=font,
                                                        color=self._palette[col_idx],
                                                        anchor_point=(0.5, 0),  ### North
                                                        anchored_position=(x_pos +1,
                                                                           scale_height),
                                                        )
                labels.append(lab)

        for minor_tick in range(0, int(vref * tick_ratio) + 1):
            x_pos = int(minor_tick * self._scale_scfactor / (vref * tick_ratio))
            for t_off_x in range(tick_width):
                scale_line[x_pos + t_off_x, scale_bottom_row] = col_idx

        tg = displayio.TileGrid(scale_line, pixel_shader=self._palette)
        if labels:
            group = displayio.Group(max_size=len(labels) + 1)
            for label in labels:
                group.append(label)
            group.append(tg)
        else:
            group = tg

        return group


    def __init__(self, width=100, height=18, output=False,
                 value=None,
                 value_range=65536, vref=3.3,
                 labels=False, font=None,
                 line_width=2, tick_width=1,
                 line_color=None, scale_color=None, bg_color=None):
        ### pylint: disable=too-many-locals
        self._palette = displayio.Palette(3)
        if bg_color is None:
            self._palette.make_transparent(0)
        else:
            self._palette[0] = bg_color

        if line_color is None:
            self._palette[self._LINE_COL_IDX] = WRITE_COLOR if output else READ_COLOR
        else:
            self._palette[self._LINE_COL_IDX] = line_color

        if scale_color is None:
            self._palette[self._SCALE_COL_IDX] = WRITE_COLOR_DIM if output else READ_COLOR_DIM
        else:
            self._palette[self._SCALE_COL_IDX] = scale_color

        self._line_scfactor = width - line_width
        self._scale_scfactor = width - tick_width
        self._value_range = value_range
        self._labels = labels
        self._font = font

        label_height = font.get_bounding_box()[1] if labels and font else 0
        scale_height = 5
        self._bargraph_line_dob = self._makeLine(line_width,
                                                 height - scale_height - label_height - 1,
                                                 self._LINE_COL_IDX)
        self._bargraph_scale_dob = self._makeScale(vref, tick_width, width,
                                                   scale_height + label_height,
                                                   self._SCALE_COL_IDX,
                                                   label_height=label_height, font=font)
        self._bargraph_scale_dob.y = height - scale_height - label_height

        self._group = displayio.Group(max_size=2)
        self._group.append(self._bargraph_line_dob)
        self._group.append(self._bargraph_scale_dob)

        self._vref = vref
        self._output = output

        self._value = None
        if value is not None:
            self.value = value


    def _setLinePos(self, value):
        if value is None:
            return
        new_x = int((self._line_scfactor + 1) * value / self._value_range)
        if self._bargraph_line_dob.x != new_x:
            self._bargraph_line_dob.x = new_x


    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if value is None:
            c_value = value
        elif value < 0:
            c_value = 0
        elif value >= self._value_range:
            c_value = self._value_range - 1
        else:
            c_value = value
        self._value = c_value
        self._setLinePos(c_value)


    @property
    def group(self):
        return self._group


### TODO - could extend this to show frequency as well
### perhaps enabled by detecting a (freq, dc) 2-tuple as value
class DisplayPinDataPWM:
    """A single cycle graph."""

    _LINE_COL_IDX = 1
    _SCALE_COL_IDX = 2

    def _makeBlankWave(self, width, height):
        wave = displayio.Bitmap(width, height, len(self._palette))
        tg = displayio.TileGrid(wave, pixel_shader=self._palette)
        return (tg, wave)


    def _makeScale(self, tick_width, width, height, col_idx):
        scale_line = displayio.Bitmap(width, height, len(self._palette))
        bottom_row = height - 1
        ticks = 5  ### (0%, 25%, 50%, 75%, 100%)

        for idx, major_tick in enumerate(range(0, ticks)):
            x_pos = int(major_tick / (ticks - 1) * self._scale_scfactor)

            for t_off_x in range(tick_width):
                for t_row in range(height):
                    scale_line[x_pos + t_off_x, t_row] = col_idx

        tg = displayio.TileGrid(scale_line, pixel_shader=self._palette)
        return (tg, scale_line)


    def __init__(self, width=100, height=18,
                 value=None, value_range=65536,
                 vref=3.3,
                 line_width=1, tick_width=1,
                 line_color=None, scale_color=None, bg_color=None):
        self._palette = displayio.Palette(3)
        if bg_color is None:
            self._palette.make_transparent(0)
        else:
            self._palette[0] = bg_color

        if line_color is None:
            self._palette[self._LINE_COL_IDX] = WRITE_COLOR
        else:
            self._palette[self._LINE_COL_IDX] = line_color

        if scale_color is None:
            self._palette[self._SCALE_COL_IDX] = WRITE_COLOR_DIM
        else:
            self._palette[self._SCALE_COL_IDX] = scale_color

        self._line_scfactor = width - line_width
        self._scale_scfactor = width - tick_width
        self._value_range = value_range
        scale_height = 3
        self._cycle_wave_width = width
        self._cycle_wave_height = height - scale_height - 3
        self._cycle_wave_dob, self._cycle_wave_bitmap = self._makeBlankWave(self._cycle_wave_width,
                                                                            self._cycle_wave_height)
        self._cycle_scale_dob, _ = self._makeScale(tick_width, width, scale_height,
                                                   self._SCALE_COL_IDX)
        self._cycle_scale_dob.y = height - scale_height
        self._cycle_scale_x_pos = self._waveXPos(value)

        self._group = displayio.Group(max_size=2)
        self._group.append(self._cycle_scale_dob)
        self._group.append(self._cycle_wave_dob)

        self._value = None
        if value is not None:
            self.value = value


    def _waveXPos(self, value):
        """Calculate the x position based on value of the the negative edge of the
           cycle. None returns None and 0 and full scale for CP mode returns "high",
           other values return an x position
           between 0 and furthest right pixel column."""
        if value is None:
            return None
        elif value == 0:
            return "low"
        elif self._value_range >= 65536 and value == self._value_range - 1:
            ### Special case for CircuitPython which treats 65535 as 100% d/c
            return "high"
        else:
            return int((self._line_scfactor + 1) * value / self._value_range)


    def _redrawWave(self, value):
        """Draw one cycle of the square wave to show the duty cycle of the
           pulse-width modulation output.
           Special values are 0 for low output and
           65535 for CircuitPython high output.
           """
        ##tg_bmp = self._group.pop()  ### Prevent redraw during modification

        ### Calculate new x position and proceed no further if already there
        negedge_x = self._waveXPos(value)
        if negedge_x == self._cycle_scale_x_pos:
            return
        else:
            self._cycle_scale_x_pos = negedge_x

        bmp = self._cycle_wave_bitmap
        bmp.fill(0)  ### clear it

        if value is None:
            return

        if negedge_x in ("low", "high"):
            y_level = 0 if negedge_x == "high" else self._cycle_wave_height - 1
            for x_pos in range(self._cycle_wave_width):
                bmp[x_pos, y_level] = self._LINE_COL_IDX

        else:
            top_y = 0

            for y_pos in range(top_y, self._cycle_wave_height):
                bmp[0, y_pos] = self._LINE_COL_IDX  ### up, rising edge

            for x_pos in range(1, negedge_x):
                bmp[x_pos, top_y] = self._LINE_COL_IDX  ### top across

            if negedge_x != 0:  ### rising edge covers x==0
                for y_pos in range(top_y, self._cycle_wave_height):
                    bmp[negedge_x, y_pos] = self._LINE_COL_IDX  ### down

            ### bottom across
            for x_pos in range(negedge_x + 1, self._cycle_wave_width):
                bmp[x_pos, self._cycle_wave_height - 1] = self._LINE_COL_IDX

        ##self._group.append(tg_bmp)  ### Restore the TileGrid holding bitmap


    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if value is None:
            c_value = value
        elif value < 0:
            c_value = 0
        elif value >= self._value_range:
            c_value = self._value_range - 1
        else:
            c_value = value
        if self._value != c_value:
            self._value = c_value
            self._redrawWave(c_value)


    @property
    def group(self):
        return self._group


class DisplayPinDataBooleanText:
    """A base class for anything that's boolean using a text representation."""

    _FALSE_TEXT = "False"
    _TRUE_TEXT = "True"
    _TEXT_MAXLEN = max(len(_FALSE_TEXT), len(_TRUE_TEXT))
    ### TODO - max length may be better set here

    def __init__(self, width=100, height=18, output=False,
                 vref=3.3,
                 value=None, value_range=65536,
                 font=terminalio.FONT, text_color=None, bg_color=None):

        if text_color is None:
            digstate_color = WRITE_COLOR if output else READ_COLOR
        else:
            digstate_color = text_color

        self._dio_font = font
        font_bb = self._dio_font.get_bounding_box()
        scale = height // (font_bb[1] * 9 // 14)

        self._value_range = value_range
        self._digstate_dob = adafruit_display_text.label.Label(text="",
                                                               max_glyphs=max(len(self._FALSE_TEXT),
                                                                              len(self._TRUE_TEXT)),
                                                               font=self._dio_font,
                                                               color=digstate_color,
                                                               background_color=bg_color,
                                                               scale=scale)
        self._digstate_dob.y = (height - 1) // 2
        self._group = displayio.Group(max_size=1)
        self._group.append(self._digstate_dob)

        self._vref = vref
        self._output = output

        self._value = None
        if value is not None:
            self.value = value


    def _setDigstate(self, value):
        if value is None:
            self._digstate_dob.text = ""
        else:
            self._digstate_dob.text = self._TRUE_TEXT if value else self._FALSE_TEXT


    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        new_value = None if value is None else bool(value)
        if self._value != new_value:
            self._value = new_value
            self._setDigstate(new_value)


    @property
    def group(self):
        return self._group


class DisplayPinDataDigital(DisplayPinDataBooleanText):
    """A text low or HIGH."""

    _FALSE_TEXT = "low"
    _TRUE_TEXT = "HIGH"
    _TEXT_MAXLEN = max(len(_FALSE_TEXT), len(_TRUE_TEXT))


class DisplayPinDataTouch(DisplayPinDataBooleanText):
    """Text with ----- or touch."""

    _FALSE_TEXT = "-----"
    _TRUE_TEXT = "Touch"
    _TEXT_MAXLEN = max(len(_FALSE_TEXT), len(_TRUE_TEXT))


class DisplayPinDataMusic:
    """A note name as a string or frequency as a number."""
    def __init__(self, width=100, height=18, output=True,
                 value=None, value_range=65536,
                 font=terminalio.FONT, text_color=None, bg_color=None):

        if text_color is None:
            note_color = WRITE_COLOR
        else:
            note_color = text_color

        self._dio_font = font
        font_bb = self._dio_font.get_bounding_box()
        scale = height // (font_bb[1] * 18 // 28)

        self._value_range = value_range
        self._note_dob = adafruit_display_text.label.Label(text="",
                                                           max_glyphs=7,  ### TODO
                                                           font=self._dio_font,
                                                           color=note_color,
                                                           background_color=bg_color,
                                                           scale=scale)
        self._note_dob.y = (height - 1) // 2
        self._group = displayio.Group(max_size=1)
        self._group.append(self._note_dob)

        self._value = None
        if value is not None:
            self.value = value


    def _setNote(self, value):
        if value is None:
            self._note_dob.text = ""
        elif isinstance(value, str):
            parts = value.split(":")
            self._note_dob.text = parts[0]
        else:
            ### TODO - this is 7 chars - maybe truncate to first 5 or 6 to keep shorter if needed
            ### and based on a dynamic value?
            self._note_dob.text = "{:d}Hz".format(round(value))
            ##self._note_dob.text = "{:.1f}Hz".format(value)
            ##self._note_dob.text = "{:d}".format(round(value))


    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self._value != value:
            self._value = value
            ### Alternative form is frequency, name, e.g 262, "C4"
            if isinstance(value, str):
                text_value = value
            else:
                text_value = value[0] if value[1] is None else value[1]
            self._setNote(text_value)


    @property
    def group(self):
        return self._group
