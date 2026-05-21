package com.doit.entityradar.client;

import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.KeyMapping;
import org.lwjgl.glfw.GLFW;

public final class RadarKeys {
    public static final KeyMapping TOGGLE = new KeyMapping(
            "key.entityradar.toggle",
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_R,
            "key.categories.entityradar");

    private RadarKeys() {}
}
