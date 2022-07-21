**Chunk Slicer Addon**

Slices object into uniform chunks.

Default hotkey: <kb>Alt</kb>+<kb>Shift</kb>+/`

*Options:*

__Slice Type:__ Whether to slice based on a fix real-world size, or relative to the objects size in all 3 dimensions.
__Cell Size:__ Size of slices in world units if Slice Type is Fixed.
__Slice Quantity:__ Number of slices per axis if Slice Type is Relative.
__Cleanup Threshold:__ If object is smaller than this size on more than one axis it will be deleted after slice operation.
__Reset Origins:__ Reset each new chunk object to center of geometry.
__Fill:__ Slice into solid individual chunks, as opposed to slicing the current geometry and keep it as is. Like boolean intersect vs knife project.
__Force:__ Force slicing of non-manifold geometry, operator results may be messy/unexpected, especially if Fill is also enabled.
