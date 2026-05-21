package com.doit.entityradar;

import com.doit.entityradar.client.RadarKeys;
import com.doit.entityradar.client.RadarOverlay;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterGuiOverlaysEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.client.gui.overlay.VanillaGuiOverlay;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.config.ModConfig;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;

@Mod(EntityRadar.MODID)
public class EntityRadar {
    public static final String MODID = "entityradar";

    public EntityRadar() {
        IEventBus modBus = FMLJavaModLoadingContext.get().getModEventBus();

        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, RadarConfig.SPEC);

        // Client-only setup. The radar is purely cosmetic, so guard registration to the client dist.
        modBus.addListener(this::registerOverlays);
        modBus.addListener(this::registerKeys);
    }

    private void registerOverlays(final RegisterGuiOverlaysEvent event) {
        event.registerAbove(VanillaGuiOverlay.HOTBAR.id(), "entity_radar", new RadarOverlay());
    }

    private void registerKeys(final RegisterKeyMappingsEvent event) {
        event.register(RadarKeys.TOGGLE);
    }
}
