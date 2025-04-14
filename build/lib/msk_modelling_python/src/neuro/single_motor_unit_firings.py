import numpy as np
import matplotlib.pyplot as plt

import numpy as np
import matplotlib.pyplot as plt

def action_potential(time, amplitude=30, rise_time=1, decay_time=3, afterhyperpolarization=10):
  """Approximates an action potential.

  Args:
    time: Time points.
    amplitude: Peak amplitude of the action potential.
    rise_time: Time constant for the rising phase.
    decay_time: Time constant for the falling phase.
    afterhyperpolarization: Amplitude of the afterhyperpolarization.

  Returns:
    The approximated membrane potential.
  """

  depolarization = amplitude * (1 / (1 + np.exp(-time / rise_time)))
  repolarization = amplitude * np.exp(-(time - rise_time) / decay_time)
  afterhyperpolarization = -afterhyperpolarization * np.exp(-(time - decay_time) / 2)
  return depolarization - repolarization + afterhyperpolarization

# Example usage:


# Example usage
if __name__ == "__main__":
    time = np.linspace(0, 0.0001, 10 )
    vm = action_potential(time)

    plt.plot(time, vm)
    plt.xlabel("Time (ms)")
    plt.ylabel("Vm (mV)")
    plt.title("Approximated Action Potential")
    plt.grid(True)
    plt.show()

