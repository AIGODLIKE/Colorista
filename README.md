
<a href="./README.md"><img src="https://img.shields.io/badge/🇬🇧English-0b8cf5"  width="100"></a>
<a href="./READMECN.md"><img src="https://img.shields.io/badge/🇨🇳中文简体-e9e9e9" width="100"></a>
## Colorista
<a href="https://space.bilibili.com/1220061774">
  <img src="https://github.com/user-attachments/assets/7bf4d809-ae68-4bfc-a49f-bdefc1f149d0" alt="image" width="150">
</a>

A convenient color grading add-on for colorists. Build AgX color grading panels in one click and preview results in real time in the viewport.

---

## Features

- One-click access to real-time color grading
- Dedicated color grading panel
- Synchronized color management
- History support
- Preset support
- Chinese and English UI

### Observation Module

After grading, enable this parameter. At `0.5`, the left side shows the original image and the right side shows the graded result. To swap sides (graded on the left, original on the right), enter a negative value such as `-0.5`.

---

### Correction Series

**Optimize Image**  
For best results, set this to the maximum. It improves overall image quality, especially with AgX and Filmic, and also helps with Standard and Khronos PBR Neutral.

During animation, each frame may look different, so this parameter can cause slight grading inconsistencies between frames. For more consistency, use a negative value; the effect will be weaker.

**Auto White Balance**  
Automatically adjusts white balance. Most effective when the image has large white areas.  
Tip: Adjust white balance first. Changing it after other grading steps can produce inaccurate colors.

**Color Temperature (Human Eye)**  
Unlike traditional color temperature, this simply shifts the image toward cooler or warmer tones. Traditional color temperature is precise; this control only leans the image cooler or warmer.

**Color Shift**  
Adjusts the color cast of the image. The effect updates immediately when you pick a color.

---

### Exposure Series

**Brightness**  
Adjusts overall brightness more gently than Exposure.

**Exposure**  
Adjusts overall brightness more strongly than Brightness.

---

### Light and Shadow Adjustment Series

**Highlights**  
Fine control over highlight brightness with high precision.

**Bright Areas**  
Adjusts the brighter regions of the image.

**Shadows**  
Adjusts the shadow regions of the image.

**Dark Areas**  
Adjusts the darkest regions of the image.

---

### Contrast Series

**Contrast Focus**  
Increases contrast while clarifying details so they read more clearly.

**Depth**  
Increases contrast while strengthening depth and dimensionality for a more layered look.

---

### Visual Clarity Series

**Texture**  
Enhances mid-level detail without changing overall contrast or edge detail. Softens or strengthens subtle surfaces such as skin or object texture.

**Clarity**  
Enhances local contrast, usually mid-frequency detail, so the image looks sharper and more dimensional. High values darken the image; keep this moderate.

**Natural Sharpening**  
Adds delicate sharpening without noise or contrast side effects. Recommended at maximum. The preferred control in the Visual Clarity series.

**Noise Sharpening**  
Similar to traditional sharpening; high values may introduce noise. Best combined with Reduce Noise.

**Reduce Noise**  
Reduces noise from brightness contrast, but cannot remove noise from insufficient sampling. High values may soften detail; use with Noise Sharpening.

---

### Saturation Series
This series uses a LAB-like algorithm with clamping to avoid common compositor saturation issues. Traditional compositor tools often push saturation past safe limits, causing hue shifts and unbalanced color. These controls keep hue stable while raising saturation, so colors stay consistent.

**Multi-Level**
Raises saturation while adding saturation depth. A common approach is to increase saturation, then reduce Global saturation slightly for richer layers without oversaturation.

**Natural**
Boosts saturation mainly in low-saturation areas for a more natural, balanced look.

**Strong Color**
Boosts saturation mainly in high-saturation areas. Useful when you want vivid, striking color.

**Global**
Adjusts overall saturation when you need full control of color intensity.

---

### Desaturation Series

**Human Eye**  
When adjusting brightness perception, this accounts for brightness, saturation, and hue, making luminance levels easier to judge.

**Brightness**  
Adjusts brightness only. When used with Human Eye Desaturation, Human Eye takes precedence.

---

### Glow Series

**Range**  
Controls where glow and star-like effects appear.

**Glow Intensity**  
Controls glow strength.

**Starburst Intensity**  
Adds a star-like glow effect.

---

### Special Effects Series

**Smudge/Film Grain**  
Move left for an oil-painting blend; move right for subtle color noise, mostly along object edges. The noise is fine and easiest to see up close.

**Mosaic/Black-and-White Comic**  
Slide left for a mosaic effect; slide right for a retro black-and-white comic look.

**Lens Distortion**  
Swipe right to zoom in; swipe left to zoom out.

**Vignette**  
Positive values brighten the corners; negative values darken them.

## Create your own asset

1. Open the Compositor and connect your nodes or node groups.

2. On the label of each node or node group you want on the panel, set a serial number such as `01`, `02`, `03`, `04`.

3. Save the file under `Colorista/resource/EN/your_folder`.

4. For a thumbnail, pair `A.blend` with `A.png`.

  ![image](https://github.com/user-attachments/assets/8b65b899-2bb8-4028-9a16-afd3a98bb936)


## Limitations

- User presets are saved as JSON under the extension user data folder (Preferences shows the path). Changing the asset template does not update existing presets; save again after structural changes.
- Incorrect ACES setups are not recommended.

## Credits

[朔朔的搅拌机日常](https://space.bilibili.com/1220061774) provided the principal grading node graphs that made this tool possible.

[KarryCharon](https://space.bilibili.com/319473039) developed the add-on code.

[BlenderCN-LJ](https://space.bilibili.com/35723238) handled debugging, documentation, and promotion.
