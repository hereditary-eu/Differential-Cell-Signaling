<script>
	import { colorScale, sender, receiver, aesSettings } from "$lib/stores";
</script>
<svg width="0" height="0" style="position:absolute; pointer-events:none;">
    <defs>
        <marker
            id="arrow"
            viewBox="0 -5 10 10"
            refX="9"
            refY="0"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
        >
            <path d="M0,-5L10,0L0,5" fill="#999" />
        </marker>
        <marker
            id="Tblunt"
            viewBox="-2 -6 4 12"
            refX="1"
            refY="0"
            markerWidth="10"
            markerHeight="10"
            orient="auto"
        >
            <path d="M0,-6L0,6" stroke="#999" stroke-width="2" />
        </marker>
        <marker
            id="leg-arrow"
            viewBox="0 -3 6 6"
            refX="5"
            refY="0"
            markerWidth="4"
            markerHeight="4"
            orient="auto"
        >
            <path d="M0,-3L6,0L0,3" fill="#999" />
        </marker>
        <marker
            id="leg-blunt"
            viewBox="-2 -4 4 8"
            refX="1"
            refY="0"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
        >
            <line x1="0" y1="-4" x2="0" y2="4" stroke="#999" stroke-width="1.5" />
        </marker>
    </defs>
</svg>

<div
	id="network-legend"
	style="
		position:absolute;
		top:8px;
		left:8px;
		z-index:10;
		background:rgba(255,255,255,0.88);
		border:1px solid #ddd;
		border-radius:5px;
		padding:6px 10px;
		font-size:11px;
		line-height:1.7;
		font-family:Arial,sans-serif;
		pointer-events:none;
	"
>
    {#if $aesSettings.CT}
        <div style="font-weight: 600; margin-bottom: 2px;">Cell types</div>
        {#each ($colorScale.domain().filter(d => d === $sender || d === $receiver)) as ct}
            <div style="white-space: nowrap;">
                <span style="
                    display:inline-block; width:10px; height:10px;
                    background:{$colorScale(ct)}; border-radius:2px; flex-shrink:0;
                "></span>
                <span>{ct}</span>
            </div>
        {/each}
    {/if}
    <div style="font-weight: 600; margin-top: 6px; margin-bottom: 2px;">Molecule</div>
    <div style="white-space: nowrap;">
        <svg width="12" height="12" style="vertical-align: middle; margin-right: 5px;"><circle cx="6" cy="6" r="5" fill="#555"/></svg>
        <span style="vertical-align: middle;">TF</span>
    </div>
    <div style="white-space: nowrap;">
        <svg width="12" height="12" style="vertical-align: middle; margin-right: 5px;"><polygon points="6,1 11,11 1,11" fill="#555"/></svg>
        <span style="vertical-align: middle;">Ligand</span>
    </div>
    <div style="white-space: nowrap;">
        <svg width="12" height="12" style="vertical-align: middle; margin-right: 5px;"><rect x="1" y="1" width="10" height="10" fill="#555"/></svg>
        <span style="vertical-align: middle;">Receptor</span>
    </div>

    {#if $aesSettings.LR !== 'reset'}
        <div style="font-weight: 600; margin-top: 6px; margin-bottom: 2px;">LR diff.</div>
        <div style="white-space: nowrap;">
            <svg width="16" height="4" style="vertical-align: middle; margin-right: 5px;"><line x1="0" y1="2" x2="16" y2="2"
                stroke={$aesSettings.LR === 'volcano' ? '#b2182b' : '#440154'} stroke-width="2"/></svg>
            <span style="vertical-align: middle;">Up</span>
        </div>
        <div style="white-space: nowrap;">
            <svg width="16" height="4" style="vertical-align: middle; margin-right: 5px;"><line x1="0" y1="2" x2="16" y2="2"
                stroke={$aesSettings.LR === 'volcano' ? '#2166ac' : '#fde725'} stroke-width="2"/></svg>
            <span style="vertical-align: middle;">Down</span>
        </div>
    {/if}

    {#if $aesSettings.TF === 'endShape'}
        <div style="font-weight: 600; margin-top: 6px; margin-bottom: 2px;">TF regulation</div>
        <div style="white-space: nowrap;">
            <svg width="16" height="8" style="vertical-align: middle; margin-right: 5px;">
                <line x1="0" y1="4" x2="12" y2="4" stroke="#999" stroke-width="1.5" marker-end="url(#leg-arrow)"/>
            </svg>
            <span style="vertical-align: middle;">Promoting</span>
        </div>
        <div style="white-space: nowrap;">
            <svg width="16" height="8" style="vertical-align: middle; margin-right: 5px;">
                <line x1="0" y1="4" x2="12" y2="4" stroke="#999" stroke-width="1.5" marker-end="url(#leg-blunt)"/>
            </svg>
            <span style="vertical-align: middle;">Inhibiting</span>
        </div>
    {/if}
</div>
