// DCM Quality Preset - Better Visuals
"GameInfo"
{
    game        "citadel"
    title       "Citadel"
    type        multiplayer_only
    nomodels 1
    nohimodel 1
    nocrosshair 0
    hidden_maps
    {
        "test_speakers"         1
        "test_hardware"         1
    }
    nodegraph 0
    perfwizard 0
    tonemapping 0 
    GameData    "citadel.fgd"
    
    Localize
    {
        DuplicateTokensAssert   1
        DisallowTokenContexts   1
    }

    SupportedLanguages
    {
        "brazilian" "3"
        "czech" "3"
        "english" "3"
        "french" "3"
        "german" "3"
        "italian" "3"
        "indonesian" "3"
        "japanese" "3"
        "koreana" "3"
        "latam" "3"
        "polish" "3"
        "russian" "3"
        "schinese" "3"
        "spanish" "3"
        "thai" "3"
        "turkish" "3"
        "ukrainian" "3"
    }
    
    FileSystem
    {   
        SearchPaths
        {  
            Game_Language       citadel_*LANGUAGE*
            Game                citadel/addons
            Mod                 citadel
            Write               citadel          
            Game                citadel
            Mod                 core
            Write               core
            Game                core        
        }
    }
    
    MaterialSystem2
    {
        RenderModes
        {
            game Default
            game Forward
            game Deferred
            game Outline
            game Depth
            game FrontDepth
            dev ToolsVis
            dev ToolsWireframe
            tools ToolsUtil
        }
    }

    MaterialEditor
    {
        "DefaultShader" "environment_texture_set"
    }

    NetworkSystem
    {
        BetaUniverse
        {
            FakeLag         0
            FakeLoss        0
            FakeReorderPct 0
            FakeReorderDelay 0
            FakeJitter "off"
        }
        "SkipRedundantChangeCallbacks"  "1"
    }

    RenderSystem
    {
        IndexBufferPoolSizeMB 32
        UseReverseDepth 1
        Use32BitDepthBuffer 0
        Use32BitDepthBufferWithoutStencil 0
        SwapChainSampleableDepth 1
        VulkanMutableSwapchain 1
        "LowLatency" "1"
        "MinStreamingPoolSizeMB" "2048"
    }

    NVNGX
    {
        AppID 103371621
        SupportsDLSS 1
    }

    Engine2
    {
        HasModAppSystems 1
        Capable64Bit 1
        URLName citadel
        RenderingPipeline
        {
            SupportsMSAA 0
            DistanceField 1
        }
        PauseSinglePlayerOnGameOverlay 1
        DefensiveConCommands 1
        DisableLoadingPlaque 1
    }

    SoundSystem
    {
        SteamAudioEnabled "1"
        WaveDataCacheSizeMB "256"
        "UsePlatTime" "1"
    }

    pulse
    {
        "pulse_enabled" "1"
    }

    SceneSystem
    {
        GpuLightBinner 1
        VolumetricFog 1
        Tonemapping 0
        ComputeShaderSkinning 1
    }

    ConVars
    {    
// DCM Quality Preset - Enhanced Visuals
// For high-end PCs that want better graphics

fps_max "0"
fps_max_ui "120"

// Shadows - High
r_shadows "1"
r_citadel_shadow_quality "3"

// Lighting - High
lb_enable_stationary_lights "1"
lb_enable_dynamic_lights "1"
r_ssao "1"
r_ssao_strength "1.0"

// Effects - High
r_effects_bloom "1"
r_depth_of_field "1"
r_particle_max_detail_level "3"
sc_clutter_enable "1"
r_grass_quality "2"

// Textures - High
r_texture_stream_mip_bias "0"
r_texturefilteringquality "4"

// Rendering
r_farz "16000"
r_size_cull_threshold "0.5"

// UI
panorama_disable_blur "0"
panorama_disable_box_shadow "0"

// Outlines
r_citadel_npr_outlines "1"
r_citadel_outlines "1"

// Network
"rate" { "min" "98304" "default" "786432" "max" "1000000" }
"cl_interp_ratio" "2"
    }
}
