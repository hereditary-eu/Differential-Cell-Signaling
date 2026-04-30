<script>
	import { colorScale, sender, receiver, aesSettings } from "$lib/stores";
</script>

<!-- this is to placed inside a div with style as follows, which contains also Network vis -->
<!-- <div style="position: relative; width: 100%; height: 100%;"> -->

<div style="
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 10;
    background: rgba(255,255,255,0.88);
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 11px;
    line-height: 1.7;
    pointer-events: none;
">
    {#if $aesSettings.CT}
        <div style="font-weight: 600; margin-bottom: 2px;">Cell types</div>
        {#each ($colorScale.domain().filter(d => d === $sender || d === $receiver)) as ct}
            <div style="display:flex; align-items:center; gap:5px;">
                <span style="
                    display:inline-block; width:10px; height:10px;
                    background:{$colorScale(ct)}; border-radius:2px; flex-shrink:0;
                "></span>
                <span>{ct}</span>
            </div>
        {/each}
    {/if}
    <div style="font-weight: 600; margin-top: 6px; margin-bottom: 2px;">Molecule</div>
    <div style="display:flex; align-items:center; gap:5px;">
        <svg width="12" height="12"><circle cx="6" cy="6" r="5" fill="#555"/></svg>
        <span>TF</span>
    </div>
    <div style="display:flex; align-items:center; gap:5px;">
        <svg width="12" height="12"><polygon points="6,1 11,11 1,11" fill="#555"/></svg>
        <span>Ligand</span>
    </div>
    <div style="display:flex; align-items:center; gap:5px;">
        <svg width="12" height="12"><rect x="1" y="1" width="10" height="10" fill="#555"/></svg>
        <span>Receptor</span>
    </div>

    {#if $aesSettings.LR !== 'reset'}
        <div style="font-weight: 600; margin-top: 6px; margin-bottom: 2px;">LR diff.</div>
        <div style="display:flex; align-items:center; gap:5px;">
            <svg width="16" height="4"><line x1="0" y1="2" x2="16" y2="2"
                stroke={$aesSettings.LR === 'volcano' ? '#b2182b' : '#440154'} stroke-width="2"/></svg>
            <span>Up</span>
        </div>
        <div style="display:flex; align-items:center; gap:5px;">
            <svg width="16" height="4"><line x1="0" y1="2" x2="16" y2="2"
                stroke={$aesSettings.LR === 'volcano' ? '#2166ac' : '#fde725'} stroke-width="2"/></svg>
            <span>Down</span>
        </div>
    {/if}

    {#if $aesSettings.TF === 'endShape'}
        <div style="font-weight: 600; margin-top: 6px; margin-bottom: 2px;">TF regulation</div>
        <div style="display:flex; align-items:center; gap:5px;">
            <svg width="16" height="8">
                <defs>
                    <marker id="leg-arrow" viewBox="0 -3 6 6" refX="5" refY="0"
                        markerWidth="4" markerHeight="4" orient="auto">
                        <path d="M0,-3L6,0L0,3" fill="#999"/>
                    </marker>
                </defs>
                <line x1="0" y1="4" x2="12" y2="4" stroke="#999" stroke-width="1.5" marker-end="url(#leg-arrow)"/>
            </svg>
            <span>Promoting</span>
        </div>
        <div style="display:flex; align-items:center; gap:5px;">
            <svg width="16" height="8">
                <defs>
                    <marker id="leg-blunt" viewBox="-2 -4 4 8" refX="1" refY="0"
                        markerWidth="6" markerHeight="6" orient="auto">
                        <line x1="0" y1="-4" x2="0" y2="4" stroke="#999" stroke-width="1.5"/>
                    </marker>
                </defs>
                <line x1="0" y1="4" x2="12" y2="4" stroke="#999" stroke-width="1.5" marker-end="url(#leg-blunt)"/>
            </svg>
            <span>Inhibiting</span>
        </div>
    {/if}
</div>
