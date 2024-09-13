
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

<a>
  <img src="https://github.com/user-attachments/assets/5a89ef99-7571-45b9-a7cc-ff4986b689d0" alt="image" width="500">
</a>

**Exposure** Adjusts the overall brightness, useful for correcting overexposed or underexposed images, and adjusting the overall light level.

## limitation

· Specially designed for AGX, other modes may have slightly inferior effects

· Incorrect ACES settings are not recommended for use

## Producer


[朔朔的搅拌机日常](https://space.bilibili.com/1220061774) provided the principle node production for the color palette, which was the key to the birth of this tool.

[KarryCharon](https://space.bilibili.com/319473039) has completed the code development of the tool.

[BlenderCN-LJ](https://space.bilibili.com/35723238)is responsible for debugging, documenting, and promoting this tool.
