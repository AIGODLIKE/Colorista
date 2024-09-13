
<a href="./README.md"><img src="https://img.shields.io/badge/🇬🇧English-0b8cf5"  width="100"></a>
<a href="./READMECN.md"><img src="https://img.shields.io/badge/🇨🇳中文简体-e9e9e9" width="100"></a>
## Colorista
<a href="https://space.bilibili.com/1220061774">
  <img src="https://github.com/user-attachments/assets/7bf4d809-ae68-4bfc-a49f-bdefc1f149d0" alt="image" width="150">
</a>

A convenient color grading add-on designed for colorists, allowing for one click construction of AGX color grading panels and real-time preview of effects directly in the viewport.



## Function

· One click access to real-time color adjustment mode

· Directly available specialized color palette panel

· Support both Chinese and English

## Use

### AGX Color Space De-hazing Series

**AGX De-hazing**: Applicable to the AGX color space. When enabled, it removes the hazy appearance, significantly improving image clarity. It is recommended to maximize the parameter.


**Saturation De-hazing weight**: Adjusted when AGX De-hazing is enabled. At 0, AGX De-hazing only affects brightness; at 1, it also affects saturation. This helps prevent the image from becoming overly saturated.

**Soft De-Gray/Violent De-Grey**: Used after enabling AGX De-hazing. Soft De-hazing and Aggressive De-hazing are different de-hazing methods. The aggressive mode makes the image clearer but can be too glaring.

<a>
  <img src="https://github.com/user-attachments/assets/e6505ef4-7c30-4bc8-8fec-52024dfcc412" alt="image" width="500">
</a>

### Color Temperature, Tint, and Exposure

**Color Temperature**：Adjusts the warmth or coolness of the image. Moving left leans towards cool (blue), while moving right leans towards warm (yellow), suitable for setting the overall atmosphere.

<a>
  <img src="https://github.com/user-attachments/assets/1801c48d-887a-4956-ae2a-e30090abaa7a" alt="image" width="500">
</a>

**Tint**：Adjusts the image towards green or purple, ideal for correcting color balance and ensuring a natural tone.

**Exposure** Adjusts the overall brightness, useful for correcting overexposed or underexposed images, and adjusting the overall light level.

### Highlights/Shadows/Whites/Blacks Series

**Highlights**:Affects the brightest areas of the image. Though the range is small, the intensity enhancement is stronger than the white adjustment, ideal for fine-tuning.

**Shadows**:Adjusts the brightness of the darkest areas. The range is small, but the effect is more pronounced, with stronger impact than the black adjustment.

**Whites**:Controls the overall brightness of light areas. The range is large but the effect is subtle, suitable for broad light area adjustments.

**Blacks**:Adjusts the overall brightness of dark areas. The range is wide, and the effect is smooth, used to control the brightness level of the entire dark area.

### Saturation Series

**Intelligent Saturation**:Automatically adjusts saturation, enhancing some areas while reducing others. If the image saturation is already as desired, this parameter may not have a noticeable effect.

**Natural Saturation**:Prioritizes enhancing low-saturation areas, making the colors appear more natural, suitable for handling hazy regions.

**Contrast Saturation**:Prioritizes enhancing high-saturation areas, highlighting dominant colors and making the image more visually impactful.

**Saturation**:Controls the overall saturation, adjusting the intensity of colors, and is an essential parameter for color adjustment.

### Contrast and Sharpness Series

**Intelligent Contrast**:Adjusts based on the contrast distribution of the image. Sliding left reduces contrast automatically, with varying intensity across different regions; sliding right increases contrast, again varying by region. If the contrast is already ideal, there may be no significant change.

**Contrast**:Manually adjusts the brightness and darkness contrast, enhancing the sense of depth and making the image more three-dimensional.

**Sharpness**:Controls the sharpness or blurriness of the image.

### Desaturation

**Desaturation**:On the left, displays a black-and-white map of the image’s saturation distribution for better observation of saturation levels; on the right, shows a luminance distribution map for assessing overall brightness.

### Glow 

**Glow Intensity**:Controls the glow effect of the scene. After AGX De-hazing is enabled, the glow effect becomes more pronounced but is not mandatory.

**Glow Threshold**:Controls at what brightness level the glow effect appears. A lower threshold allows glow to appear in lower-brightness areas.

## limitation

· Specially designed for AGX, other modes may have slightly inferior effects

· Incorrect ACES settings are not recommended for use

## Producer


[朔朔的搅拌机日常](https://space.bilibili.com/1220061774) provided the principle node production for the color palette, which was the key to the birth of this tool.

[KarryCharon](https://space.bilibili.com/319473039) has completed the code development of the tool.

[BlenderCN-LJ](https://space.bilibili.com/35723238)is responsible for debugging, documenting, and promoting this tool.
