
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

· Synchronized color management

· Support historical records

![image](https://github.com/user-attachments/assets/97c37c09-dfe1-465f-b47e-d76ecdc1f576)



## Use Composer Colorista VI

### Correction Series

**Automatic White Balance** : Automatically adjusts color balance based on lighting conditions, making the whites in the image appear natural.

**Automatic Black and White Field** : This feature automatically adjusts the pure white and pure black areas in the image. It is recommended to set the parameters to maximum; the effect is best in Agx mode, while the standard mode may result in overexposure.

**Automatic Gray Field** : Automatically adjusts the gray areas, achieving excellent results in standard color space.

<a>
  <img src="https://github.com/user-attachments/assets/e6505ef4-7c30-4bc8-8fec-52024dfcc412" alt="image" width="500">
</a>


**Gamma Correction** : Applied for gamma correction.

### Brightness Adjustment Series

**Natural Exposure** : Natural exposure adjustment is also used to regulate the overall exposure level, but it has a softer effect and is less intense, making it suitable for more delicate exposure adjustments.

**Exposure Adjustment** : Used to process areas that are overexposed or approaching overexposure. By employing highlight compression, it can recover slightly overexposed highlight areas and restore details in the bright regions.

**Brightness Control** : Controls the overall brightness of the highlight areas in the image. This parameter has a wide range but offers a gentle effect, making it suitable for adjusting the highlights as a whole.

**Shadow Adjustment** : Adjusts the brightness of the shadow areas in the image. This parameter has a wide range but offers a gentle effect, making it suitable for controlling the overall brightness of the shadows in the image.

**Midtone Adjustment** : By adjusting the brightness of the midtones in the image, you can further optimize the overall balance. This adjustment helps maintain the image’s sense of depth and layering.

**Highlight Adjustment** : Specifically adjusts the brightness of the brightest areas in the image. Compared to the “Whites” adjustment, it has a narrower range but a stronger effect, making it suitable for fine-tuning the highlight regions.

**Shadow Adjustment** : Adjusts the brightness of the darkest areas in the image. This adjustment has a narrower range but a more pronounced effect compared to the “Blacks” adjustment, making it suitable for fine-tuning the brightness of the shadow regions.

### Contrast Series

**Intelligent Contrast** : Intelligent contrast offers a more nuanced adjustment approach, selectively affecting the contrast of different areas in the image. It is recommended to set this parameter to the maximum value initially and then make adjustments based on the actual effect to achieve the best results.

**Contrast** : Contrast is a key parameter that affects the brightness differences in an image, reflecting the degree of difference between the brightest and darkest parts. By appropriately adjusting the contrast, you can enhance the visual depth and sense of layering in the image.

### Visual Clarity Series

**Clarity** : This parameter is specifically designed to enhance the local contrast of an image, often used to boost mid-frequency details. By doing so, it makes the image appear more three-dimensional and sharper.

**Texture** : This parameter is primarily used to adjust mid-level details. It does not affect the overall contrast or edge details but focuses on enhancing or softening subtle details in the image, such as skin texture or the surface texture of objects.

**Natural Sharpening** : Natural sharpening is a technique that enhances the sharpness of an image without introducing noise and with minimal halo effects. Compared to clarity adjustments, natural sharpening allows for more precise control over the image’s sharpness without significantly affecting the contrast of larger areas. This method ensures that fine details are enhanced while maintaining a natural appearance, making it particularly useful for preserving the integrity of textures and details without compromising overall image quality.

**Sharpening** : Similar to traditional sharpening tools, excessively high sharpening values can introduce image noise and may cause the overall image to darken. It is advisable to use this adjustment in conjunction with a noise reduction parameter. A common recommendation is to set the noise reduction value to about half of the sharpening value to effectively mitigate the noise introduced by sharpening while preserving detail. This balanced approach helps maintain image quality and ensures that enhancements do not compromise the overall appearance.

**Noise Reduction** : Noise reduction is used to minimize the noise in an image caused by contrast between light and dark areas. However, it is important to note that this adjustment cannot eliminate noise resulting from under-sampling. If the noise reduction value is set too high, it may lead to a loss of fine details in the image. Therefore, it is recommended to use it in conjunction with sharpening tools, where the noise reduction value is ideally set to about half of the sharpening value. This balanced approach helps maintain detail while effectively reducing noise, resulting in a cleaner and more visually appealing image.

### Color Tone Adjustment

**Scene Hue Shift (RGB)** : Regular Adjustment of Scene Hue.

**Scene Hue Shift (Lab)** : Adjusting Scene Hue in LAB Mode.

**Color Temperature (Cool/Warm)** : Adjusting the color temperature can shift the image towards cooler or warmer tones. Lowering the color temperature value will make the image cooler (with a blue tint), while increasing the color temperature will make the image warmer (with a yellow or orange tint).

<a>
  <img src="https://github.com/user-attachments/assets/1801c48d-887a-4956-ae2a-e30090abaa7a" alt="image" width="500">
</a>


**Dyeing Target Color** : Users can choose the target color they want the image to lean towards. Once the color is selected, the overall color tendency of the image can be adjusted by modifying the dyeing intensity.

**Target Color Dyeing Intensity** : Control the dyeing intensity of the currently selected target color. The higher the dyeing intensity value, the stronger the image’s color tendency towards the target color; conversely, a lower value will result in a weaker tendency.

### Saturation Series

**Intelligent Saturation** : Intelligent saturation is a more refined tool that selectively adjusts the saturation of certain areas based on the image’s contrast and existing saturation distribution, making the adjustment effect more precise. It is recommended to initially set it to the highest value and then gradually it while observing the image to achieve the best results.

**Natural Saturation** : This parameter primarily focuses on areas of low saturation in the image, aiming to maintain a natural look and avoid making colors appear overly exaggerated or distorted.

**Contrast Saturation** : Focuses on areas of high saturation in the image; excessively high values may lead to color distortion or make the image appear unnatural. Moderate adjustments can enhance or reduce the contrast effect in these areas.

**Saturation** : Saturation directly affects the intensity or vividness of colors in an image. Increasing saturation makes colors more vibrant, while decreasing saturation results in softer colors.

### Desaturation

**Desaturation (Saturation/Contrast)** : Observe the saturation distribution on the left and the brightness distribution on the right.

### Suosuo Effects Series

**Glow Intensity** : Control the glow effect of the scene.

**Starburst Intensity** : Create a star-like glow effect in the scene.

** Lens Distortion** : Distort the lens; sliding to the right shows color, while sliding to the left shows no color.

**Blend Colors/Film Grain** : The film grain is very subtle.

**Mosaic Effect/Black and White Striped Pattern** : It will transition to the feel of early black and white comics as you move to the right.

### RGB Curves

### Color Balance

### Hue Correct

## Create your own presets

1. Open the Composing panel and connect your nodes/node groups.
   
2. On the label of the node/node group you want to display on the panel, fill in the serial number, such as 01, 02, 03, 04, etc
   
3. Save the file and place it in the Colorista \ resource \ EN \ your folder
   
4. If you need a thumbnail, you can consider A The combination of Blend and A.png

   ![image](https://github.com/user-attachments/assets/5ff67630-6f23-4902-ba9f-f167f1a9fb65)


## limitation

· Incorrect ACES settings are not recommended for use

## Producer


[朔朔的搅拌机日常](https://space.bilibili.com/1220061774) provided the principle node production for the color palette, which was the key to the birth of this tool.

[KarryCharon](https://space.bilibili.com/319473039) has completed the code development of the tool.

[BlenderCN-LJ](https://space.bilibili.com/35723238)is responsible for debugging, documenting, and promoting this tool.
