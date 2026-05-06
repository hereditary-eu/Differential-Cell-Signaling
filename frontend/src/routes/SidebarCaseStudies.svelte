<!-- component for choosing between FMD and ALS case studies or upload data -->

<script lang="ts">
	import { onMount } from 'svelte';
	import { selectedCaseStudy, selectedComparison } from '$lib/stores';

	let tooltips = {
		ALS: 'Differential signalling inferred from snRNA-seq data publicly available from Pineda et al. (2024) https://doi.org/10.1016/j.cell.2024.02.031',
		C9ALS_vs_PN:
			'Differential signalling in familial ALS ("C9ALS", i.e. carrying hexanucleotide repeat expansion on C9orf72) compared to an healthy reference ("PN", i.e. Pathologically Normal).',
		SALS_vs_PN:
			'Differential signalling in sporadic ALS ("SALS") compared to an healthy reference ("PN", i.e. Pathologically Normal).',
		SALS_vs_C9ALS:
			'Differential signalling in sporadic ALS ("SALS") compared to familial ALS ("C9ALS", i.e. carrying hexanucleotide repeat expansion on C9orf72).',
		FMD: "Differential signalling inferred from scRNA-seq data publicly available from d'Escamard et al. (2024) https://doi.org/10.1038/s44161-024-00533-w",
		Ko_vs_Wt:
			'Differential signalling in FMD Ko mouse model, carrying Ubr4 knockout on smooth muscle cells, compared to wild type (Wt) mice.'
	};
	onMount(() => {
		// set default case study and comparison on initial load
		selectedCaseStudy.set('ALS');
		selectedComparison.set('C9ALS_vs_PN');
	});

	function handleCaseStudyChange(value: string) {
		selectedCaseStudy.set(value);
		if (value === 'FMD') {
			selectedComparison.set('Ko_vs_Wt');
		} else if (value === 'ALS') {
			selectedComparison.set('C9ALS_vs_PN');
		}
	}
</script>

<fieldset>
	<legend>Case Study</legend>

	<!-- Case Study Selection -->
	<div class="form-check tooltip-wrapper">
		<input
			type="radio"
			value="als"
			checked={$selectedCaseStudy === 'ALS'}
			on:change={() => handleCaseStudyChange('ALS')}
			class="form-check-input"
			id="als"
		/>
		<label for="als">ALS - Amyotrophic Lateral Sclerosis</label>
		<div class="tooltip">
			{tooltips.ALS}
		</div>
	</div>
	<div class="form-check tooltip-wrapper">
		<input
			type="radio"
			value="FMD"
			checked={$selectedCaseStudy === 'FMD'}
			on:change={() => handleCaseStudyChange('FMD')}
			class="form-check-input"
			id="fmd"
		/>
		<label for="fmd">FMD - Fibromuscular Dysplasia</label>
		<div class="tooltip">
			{tooltips.FMD}
		</div>
	</div>

	<div class="form-check disabled">
		<input
			class="form-check-input"
			type="radio"
			name="caseStudyOptions"
			id="upload"
			value="upload"
			disabled
		/>
		<label class="form-check-label" for="upload">Upload your own data</label>
	</div>
	<hr />
	<!-- reactive comparisons availble -->
	{#if $selectedCaseStudy === 'FMD'}
		<div class="form-check tooltip-wrapper">
			<input type="radio" value="Ko_vs_Wt" bind:group={$selectedComparison} id="ko_vs_wt" />
			<label for="ko_vs_wt">KO vs WT</label>
			<div class="tooltip">
				{tooltips.Ko_vs_Wt}
			</div>
		</div>
	{/if}
	{#if $selectedCaseStudy === 'ALS'}
		<div class="form-check tooltip-wrapper">
			<input type="radio" value="C9ALS_vs_PN" id="c9als_vs_pn" bind:group={$selectedComparison} />
			<label for="c9als_vs_pn">C9ALS vs PN</label>
			<div class="tooltip">
				{tooltips.C9ALS_vs_PN}
			</div>
		</div>

		<div class="form-check tooltip-wrapper">
			<input type="radio" value="SALS_vs_PN" id="sals_vs_pn" bind:group={$selectedComparison} />
			<label for="sals_vs_pn"> SALS vs PN</label>
			<div class="tooltip">
				{tooltips.SALS_vs_PN}
			</div>
		</div>

		<div class="form-check tooltip-wrapper">
			<input
				type="radio"
				value="SALS_vs_C9ALS"
				id="sals_vs_c9als"
				bind:group={$selectedComparison}
			/>
			<label for="sals_vs_c9als">SALS vs C9ALS</label>
			<div class="tooltip">
				{tooltips.SALS_vs_C9ALS}
			</div>
		</div>
	{/if}
</fieldset>

<style>
	.tooltip-wrapper {
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.tooltip {
		position: absolute;
		left: 100%;
		top: 50%;
		transform: translateY(-50%);
		transform: translateX(-96%);
		margin-left: 0px;
		width: max-content;
		max-width: 250px;
		opacity: 0;
		pointer-events: none;
		transition: opacity 0.2s;
		
		background: #333;
		color: white;
		padding: 6px 10px;
		border-radius: 6px;
	}

	.tooltip-wrapper:hover .tooltip {
		opacity: 1;
	}
</style>
