package com.doit.entityradar.client;

import com.doit.entityradar.RadarConfig;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.client.gui.overlay.ForgeGui;
import net.minecraftforge.client.gui.overlay.IGuiOverlay;

import java.util.List;

public class RadarOverlay implements IGuiOverlay {

    private static final int COLOR_HOSTILE = 0xFFFF5555;
    private static final int COLOR_PASSIVE = 0xFF55FF55;
    private static final int COLOR_PLAYER  = 0xFFFFFFFF;
    private static final int COLOR_ITEM    = 0xFFFFDD55;
    private static final int COLOR_SELF     = 0xFF44AAFF;
    private static final int COLOR_RING     = 0x66FFFFFF;

    private static boolean runtimeEnabled = true;

    @Override
    public void render(ForgeGui gui, GuiGraphics g, float partialTick, int screenWidth, int screenHeight) {
        // Toggle key: poll here so we don't need a separate tick subscriber.
        while (RadarKeys.TOGGLE.consumeClick()) {
            runtimeEnabled = !runtimeEnabled;
        }

        if (!runtimeEnabled || !RadarConfig.ENABLED.get()) return;

        Minecraft mc = Minecraft.getInstance();
        LocalPlayer player = mc.player;
        if (player == null || mc.level == null) return;
        if (mc.options.hideGui || mc.options.renderDebug) return;
        if (mc.screen != null) return;

        final int hudRadius = RadarConfig.HUD_RADIUS.get();
        final int scanRadius = RadarConfig.SCAN_RADIUS.get();
        final int dotSize = RadarConfig.DOT_SIZE.get();
        final boolean rotate = RadarConfig.ROTATE_WITH_PLAYER.get();
        final int diameter = hudRadius * 2;

        int left;
        int top;
        switch (RadarConfig.CORNER.get()) {
            case TOP_RIGHT -> {
                left = screenWidth - RadarConfig.MARGIN_X.get() - diameter;
                top = RadarConfig.MARGIN_Y.get();
            }
            case BOTTOM_LEFT -> {
                left = RadarConfig.MARGIN_X.get();
                top = screenHeight - RadarConfig.MARGIN_Y.get() - diameter;
            }
            case BOTTOM_RIGHT -> {
                left = screenWidth - RadarConfig.MARGIN_X.get() - diameter;
                top = screenHeight - RadarConfig.MARGIN_Y.get() - diameter;
            }
            default -> {
                left = RadarConfig.MARGIN_X.get();
                top = RadarConfig.MARGIN_Y.get();
            }
        }
        final int cx = left + hudRadius;
        final int cy = top + hudRadius;

        int bgOpacity = RadarConfig.BACKGROUND_OPACITY.get();
        if (bgOpacity > 0) {
            fillDisk(g, cx, cy, hudRadius, (bgOpacity << 24));
        }
        drawRing(g, cx, cy, hudRadius, COLOR_RING);

        double px = player.getX();
        double pz = player.getZ();
        double yawRad = Math.toRadians(player.getYRot());
        double lookX = -Math.sin(yawRad);
        double lookZ = Math.cos(yawRad);
        double scale = (double) hudRadius / scanRadius;

        AABB box = new AABB(
                px - scanRadius, player.getY() - scanRadius, pz - scanRadius,
                px + scanRadius, player.getY() + scanRadius, pz + scanRadius);
        List<Entity> entities = mc.level.getEntities(player, box, RadarOverlay::isShown);

        for (Entity e : entities) {
            int color = colorFor(e);
            if (color == 0) continue;

            double dx = e.getX() - px;
            double dz = e.getZ() - pz;
            if (dx * dx + dz * dz > (double) scanRadius * scanRadius) continue;

            double mapX;
            double mapY;
            if (rotate) {
                double forward = dx * lookX + dz * lookZ;
                double right = dx * (-lookZ) + dz * lookX;
                mapX = right * scale;
                mapY = -forward * scale;
            } else {
                mapX = dx * scale;
                mapY = dz * scale;
            }

            if (mapX * mapX + mapY * mapY > (double) hudRadius * hudRadius) continue;

            int sx = cx + (int) Math.round(mapX);
            int sy = cy + (int) Math.round(mapY);
            int half = dotSize / 2;
            g.fill(sx - half, sy - half, sx - half + dotSize, sy - half + dotSize, color);
        }

        // Player marker in the center.
        g.fill(cx - 1, cy - 1, cx + 2, cy + 2, COLOR_SELF);
    }

    private static boolean isShown(Entity e) {
        return colorFor(e) != 0;
    }

    private static int colorFor(Entity e) {
        if (e instanceof Player) {
            return RadarConfig.SHOW_PLAYERS.get() ? COLOR_PLAYER : 0;
        }
        if (e instanceof Enemy) {
            return RadarConfig.SHOW_HOSTILE.get() ? COLOR_HOSTILE : 0;
        }
        if (e instanceof ItemEntity) {
            return RadarConfig.SHOW_ITEMS.get() ? COLOR_ITEM : 0;
        }
        if (e instanceof LivingEntity) {
            return RadarConfig.SHOW_PASSIVE.get() ? COLOR_PASSIVE : 0;
        }
        return 0;
    }

    /** Filled disk via horizontal scanlines (GuiGraphics has no circle primitive). */
    private static void fillDisk(GuiGraphics g, int cx, int cy, int r, int argb) {
        for (int dy = -r; dy <= r; dy++) {
            int hw = (int) Math.floor(Math.sqrt((double) r * r - (double) dy * dy));
            g.fill(cx - hw, cy + dy, cx + hw + 1, cy + dy + 1, argb);
        }
    }

    /** Thin ring outline approximated by plotting points around the circle. */
    private static void drawRing(GuiGraphics g, int cx, int cy, int r, int argb) {
        int steps = Math.max(48, r * 4);
        for (int i = 0; i < steps; i++) {
            double a = (Math.PI * 2 * i) / steps;
            int x = cx + (int) Math.round(Math.cos(a) * r);
            int y = cy + (int) Math.round(Math.sin(a) * r);
            g.fill(x, y, x + 1, y + 1, argb);
        }
    }
}
