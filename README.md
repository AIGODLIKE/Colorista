
<a href="./README.md"><img src="https://img.shields.io/badge/🇬🇧English-0b8cf5"  width="100"></a>
<a href="./READMECN.md"><img src="https://img.shields.io/badge/🇨🇳中文简体-e9e9e9" width="100"></a>
## Colorista
<a href="https://space.bilibili.com/1220061774">
  <img src="https://github.com/user-attachments/assets/7bf4d809-ae68-4bfc-a49f-bdefc1f149d0" alt="image" width="150">
</a>

A convenient color grading add-on designed for colorists, allowing for one click construction of AGX color grading panels and real-time preview of effects directly in the viewport.

---

## Function

· One click access to real-time color adjustment mode

· Directly available specialized color palette panel

· Synchronized color management

· Support historical records

· Support preset settings

· Support both Chinese and English

### Correction Series

After the color adjustment is completed, turn on this parameter. When the value is 0.5, the left side is the original image and the right side is the color adjusted image. If you want the left side to be the finished color adjustment and the right side to be the original image, you can manually enter a negative number, such as 0.5



### Correction Series

**Optimize Image**  
It is highly recommended to set the value to the maximum for the best results. This parameter enhances overall image performance, excelling in AgX and Filmic effects, with some improvement in Standard and Khronos PBR Neutral.

During animation, since each frame may have different visual effects, adjusting this parameter might cause slight inconsistencies in color grading between frames. To ensure consistency between frames, you can set the value to negative, though the effect will be less pronounced.

**Auto White Balance**  
Automatically adjusts the white balance of your image, particularly effective when there are large white areas in the image.  
Suggestion: White balance should be adjusted first. Avoid adjusting it after other color grading tasks, as this may result in inaccurate colors.

**Color Temperature (Human Eye)**  
Unlike traditional color temperature, this simply shifts the image to cooler or warmer tones. Traditional color temperature is precise, but this adjustment merely leans the image toward cooler or warmer hues.

**Color Shift**  
Adjusts the color tendency of your image. You can see the effect immediately when choosing any color.

---

### Exposure Series

**Brightness**  
Adjusts the overall brightness of the image in a softer way compared to exposure.

**Exposure**  
Adjusts the overall brightness of the image in a stronger way compared to brightness.

---

### Light and Shadow Adjustment Series

**Highlights**  
Precise control over the brightness of the highlights, with high accuracy, is my proud masterpiece.

**Bright Areas**  
Adjusts the brightness of the brighter parts of the image.

**Shadows**  
Adjusts the brightness of the shadow areas of the image.

**Dark Areas**  
Adjusts the brightness of the darkest parts of the image.

---

### Contrast Series

**Contrast Focus**  
While increasing the contrast of the image, it emphasizes enhancing the clarity of details, making them more visible and precise.

**Depth**  
While increasing the contrast of the image, it focuses more on enhancing the sense of dimensionality, giving the image a more layered and three-dimensional effect.

---

### Visual Clarity Series

**Texture**  
Enhances mid-level details without affecting overall contrast or edge details. Focuses on enhancing or softening subtle details in the image, such as skin texture or object surface texture.

**Clarity**  
Enhances local contrast, typically improving mid-frequency details to make the image appear sharper and more three-dimensional. High values will darken the image, so it’s recommended to keep this setting moderate.

**Natural Sharpening**  
No noise or contrast impact, delivering a delicate and subtle effect. Recommended to set to the maximum value. This is the most recommended adjustment in the Visual Clarity series.

**Noise Sharpening**  
Similar to traditional sharpening tools, high sharpening values may introduce noise. It’s best used in combination with the "Reduce Noise" feature.

**Reduce Noise**  
Reduces noise caused by brightness contrast, but cannot eliminate noise due to insufficient sampling. High values may lose details, so it’s recommended to use in conjunction with "Noise Sharpening."

---

### Saturation Series
This series utilizes a LAB-like algorithm combined with clamping mechanisms, addressing the common issues found in traditional synthesizers when adjusting saturation. Traditional synthesizers often push saturation beyond the extreme values, causing uncontrollable hue shifts and disrupting the overall color balance. Our saturation series, however, strictly controls hue, ensuring that while saturation is increased, the hue remains stable, avoiding the typical color shift problems.

**Multi-Level**
Increases saturation while enhancing the image’s saturation layers. It is recommended to raise saturation and then globally reduce saturation, adding depth and layers to the image without causing overly intense saturation.

**Natural**
Prioritizes enhancing saturation in low-saturation areas, making the colors in the image appear more natural and harmonious.

**Strong Color**
Prioritizes enhancing saturation in high-saturation areas, ideal for scenes that require vibrant colors, giving the image a more impactful and striking appearance.

**Global**
Adjusts overall saturation, suitable for situations where you need complete control over the intensity of colors.

---

### Desaturation Series

**Human Eye**  
When adjusting brightness, this not only considers brightness but also saturation and hue. This adjustment makes it easier to observe the brightness levels of your image.

**Brightness**  
Purely adjusts brightness. When used alongside "Human Eye Desaturation," the latter takes precedence.

---

### Glow Series

**Range**  
Adjusts the range of areas where glow and star-like effects appear.

**Glow Intensity**  
Increases the intensity of the glow effect.

**Starburst Intensity**  
Adds a star-like glow effect.

---

### Special Effects Series

**Smudge/Film Grain**  
Moving left creates an oil painting-like blending effect, while moving right creates color noise that primarily appears at the edges of objects. The color noise is subtle and requires careful observation.

**Mosaic/Black-and-White Comic**  
Sliding left creates a mosaic effect, while sliding right gives a retro black-and-white comic effect.

**Lens Distortion**  
Swipe right to zoom in, swipe left to zoom out

**Vignette**

Positive values brighten the corners, negative values darken the corners.

### 

## Create your own project

1. Open the Composing panel and connect your nodes/node groups.
   
2. On the label of the node/node group you want to display on the panel, fill in the serial number, such as 01, 02, 03, 04, etc
   
3. Save the file and place it in the Colorista \ resource \ EN \ your folder
   
4. If you need a thumbnail, you can consider A The combination of Blend and A.png

  ![image](https://github.com/user-attachments/assets/8b65b899-2bb8-4028-9a16-afd3a98bb936)


## limitation

· The principle of presets is to save files. If you make changes, the presets will not be synchronized. Please save again.

· Incorrect ACES settings are not recommended for use

## Producer

[朔朔的搅拌机日常](https://space.bilibili.com/1220061774) provided the principle node production for the color palette, which was the key to the birth of this tool.

[KarryCharon](https://space.bilibili.com/319473039) has completed the code development of the tool.

[BlenderCN-LJ](https://space.bilibili.com/35723238) is responsible for debugging, documenting, and promoting this tool.
