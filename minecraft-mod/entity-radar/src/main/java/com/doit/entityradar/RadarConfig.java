package com.doit.entityradar;

import net.minecraftforge.common.ForgeConfigSpec;

public final class RadarConfig {
    public static final ForgeConfigSpec SPEC;

    public static final ForgeConfigSpec.BooleanValue ENABLED;
    public static final ForgeConfigSpec.IntValue SCAN_RADIUS;
    public static final ForgeConfigSpec.IntValue HUD_RADIUS;
    public static final ForgeConfigSpec.IntValue MARGIN_X;
    public static final ForgeConfigSpec.IntValue MARGIN_Y;
    public static final ForgeConfigSpec.EnumValue<Corner> CORNER;
    public static final ForgeConfigSpec.IntValue DOT_SIZE;
    public static final ForgeConfigSpec.IntValue BACKGROUND_OPACITY;
    public static final ForgeConfigSpec.BooleanValue ROTATE_WITH_PLAYER;

    public static final ForgeConfigSpec.BooleanValue SHOW_HOSTILE;
    public static final ForgeConfigSpec.BooleanValue SHOW_PASSIVE;
    public static final ForgeConfigSpec.BooleanValue SHOW_PLAYERS;
    public static final ForgeConfigSpec.BooleanValue SHOW_ITEMS;

    public enum Corner { TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT }

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();

        b.push("general");
        ENABLED = b.comment("Master switch for the radar (also toggleable with the keybind).")
                .define("enabled", true);
        SCAN_RADIUS = b.comment("Fixed scan radius in blocks. Entities within this distance are shown.")
                .defineInRange("scanRadius", 48, 4, 256);
        ROTATE_WITH_PLAYER = b.comment("If true, the top of the radar is the direction you face. If false, top is north.")
                .define("rotateWithPlayer", true);
        b.pop();

        b.push("hud");
        HUD_RADIUS = b.comment("Radius of the radar circle on screen, in pixels.")
                .defineInRange("hudRadius", 40, 16, 200);
        CORNER = b.comment("Which screen corner the radar anchors to.")
                .defineEnum("corner", Corner.TOP_LEFT);
        MARGIN_X = b.comment("Horizontal gap from the chosen corner, in pixels.")
                .defineInRange("marginX", 8, 0, 1000);
        MARGIN_Y = b.comment("Vertical gap from the chosen corner, in pixels.")
                .defineInRange("marginY", 8, 0, 1000);
        DOT_SIZE = b.comment("Size of each entity dot, in pixels.")
                .defineInRange("dotSize", 3, 1, 12);
        BACKGROUND_OPACITY = b.comment("Background opacity (0 = invisible, 255 = opaque).")
                .defineInRange("backgroundOpacity", 100, 0, 255);
        b.pop();

        b.push("entities");
        SHOW_HOSTILE = b.comment("Show hostile mobs (red).").define("showHostile", true);
        SHOW_PASSIVE = b.comment("Show passive/neutral mobs (green).").define("showPassive", true);
        SHOW_PLAYERS = b.comment("Show other players (white).").define("showPlayers", true);
        SHOW_ITEMS = b.comment("Show dropped items (yellow).").define("showItems", false);
        b.pop();

        SPEC = b.build();
    }

    private RadarConfig() {}
}
