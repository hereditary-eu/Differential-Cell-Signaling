<!-- component for choosing between FMD and ALS case studies or upload data -->

<script lang="ts">
	import { onMount } from 'svelte';
	import { selectedCaseStudy, selectedComparison } from '$lib/stores';

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
	<div class="form-check">
		<input
			type="radio"
			value="als"
			checked={$selectedCaseStudy === 'ALS'}
			on:change={() => handleCaseStudyChange('ALS')}
			class="form-check-input"
			id="als"
		/>
		<label for="als">ALS - Amyotrophic Lateral Sclerosis</label>
	</div>
	<div class="form-check">
		<input
			type="radio"
			value="FMD"
			checked={$selectedCaseStudy === 'FMD'}
			on:change={() => handleCaseStudyChange('FMD')}
			class="form-check-input"
			id="fmd"
		/>
		<label for="fmd">FMD - Fibromuscular Dysplasia</label>
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
		<div class="form-check">
			<input
				type="radio"
				value="Ko_vs_Wt"
				bind:group={$selectedComparison}
				class="form-check-input"
				id="ko_vs_wt"
			/>
			<label for="ko_vs_wt">KO vs WT</label>
		</div>
	{/if}
	{#if $selectedCaseStudy === 'ALS'}
		<div class="form-check">
			<input type="radio" value="C9ALS_vs_PN" id="c9als_vs_pn" bind:group={$selectedComparison} />
			<label for="c9als_vs_pn">C9ALS vs PN</label>
		</div>

		<div class="form-check">
			<input type="radio" value="SALS_vs_PN" id="sals_vs_pn" bind:group={$selectedComparison} />
			<label for="sals_vs_pn">SALS vs PN</label>
		</div>

		<div class="form-check">
			<input
				type="radio"
				value="SALS_vs_C9ALS"
				id="sals_vs_c9als"
				bind:group={$selectedComparison}
			/>
			<label for="sals_vs_c9als">SALS vs C9ALS</label>
		</div>
	{/if}
</fieldset>
