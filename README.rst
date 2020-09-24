Introduction
============

This is `CircuitPython <https://circuitpython.org/>`_ library which provides
a graphical representation of values read from or written to the
GPIO pads/pins using `displayio <https://circuitpython.readthedocs.io/en/latest/shared-bindings/displayio/>`_.


Dependencies
=============

This library depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_
* `Adafruit adafruit_display_text.label <https://github.com/adafruit/Adafruit_CircuitPython_Display_Text>`_


Usage Example
=============

.. code-block:: python

    import board
    import analogio
    import display_pin

    dp_pin1 = display_pin.DisplayPin("P1", "read_analog")
    board.DISPLAY.show(dp_pin1.group)
    pin1 = analogio.AnalogIn(board.P1)
    while True:
        dp_pin1.value = pin1.value

