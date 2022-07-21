
**Chunk Slicer Addon**

Slices object into uniform chunks.

Default hotkey: <kb>Alt</kb>+<kb>Shift</kb>+/`

__Options:__

*Slice Type:*
Whether to slice based on a fix real-world size, or relative to the objects size in all 3 dimensions.

*Cell Size:*
 Size of slices in world units if Slice Type is Fixed.

*Slice Quantity:*
Number of slices per axis if Slice Type is Relative.

*Cleanup Threshold:*
If object is smaller than this size on more than one axis it will be deleted after slice operation.

*Reset Origins:*
Reset each new chunk object to center of geometry.

*Fill:*
Slice into solid individual chunks, as opposed to slicing the current geometry and keep it as is. Like boolean intersect vs knife project.

*Force:*
 Force slicing of non-manifold geometry, operator results may be messy/unexpected, especially if Fill is also enabled.
