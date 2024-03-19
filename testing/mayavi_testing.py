import numpy as np
from mayavi.mlab import *
from mayavi import mlab
#
# test_volume_slice()
#
import numpy as np
x, y, z = np.ogrid[-10:10:20j, -10:10:20j, -10:10:20j]
s = np.sin(x*y*z)/(x*y*z)
print(s.shape)

# contour3d(s)
mlab.pipeline.volume(mlab.pipeline.scalar_field(s))
show()