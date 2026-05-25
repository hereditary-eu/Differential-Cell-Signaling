<script lang="ts">
	import { onMount } from 'svelte';
	import { selectedCaseStudy, selectedComparison } from '$lib/stores';

	let tooltips = {
		ALS: 'Differential signaling inferred from snRNA-seq data publicly available from Pineda et al. (2024) https://doi.org/10.1016/j.cell.2024.02.031',
		C9ALS_vs_PN:
			'Differential signaling in familial ALS ("C9ALS", i.e. carrying hexanucleotide repeat expansion on C9orf72) compared to an healthy reference ("PN", i.e. Pathologically Normal).',
		SALS_vs_PN:
			'Differential signaling in sporadic ALS ("SALS") compared to an healthy reference ("PN", i.e. Pathologically Normal).',
		SALS_vs_C9ALS:
			'Differential signaling in sporadic ALS ("SALS") compared to familial ALS ("C9ALS", i.e. carrying hexanucleotide repeat expansion on C9orf72).',
		FMD: "Differential signaling inferred from scRNA-seq data publicly available from d'Escamard et al. (2024) https://doi.org/10.1038/s44161-024-00533-w",
		Ko_vs_Wt:
			'Differential signaling in FMD Ko mouse model, carrying Ubr4 knockout on smooth muscle cells, compared to wild type (Wt) mice.'
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

	// user defined case study
	// let submitted = $state<{ success: Boolean, message: String }>({ success: false, message: '' });
	// type Step = 'params' | 'files' | 'sanitize' | 'review';
	// interface UploadState {
	// 	caseStudyName: string;
	// 	organism: 'human' | 'mouse';
	// 	condition: string;
	// 	refCondition: string;
	// 	splitComplexes: boolean;
	// 	cccFile: File | null;
	// 	tflFile: File | null;
	// 	sanitizeCelltypes: boolean;
	// 	sanitizeReferenceFile: File | null;
	// }
	// interface ValidationErrors {
	// 	caseStudyName?: string;
	// 	condition?: string;
	// 	refCondition?: string;
	// 	cccFile?: string;
	// 	tflFile?: string;
	// }
	// const steps: {id: Step; label: string; icon: string}[] = [
	// 	{id: 'params', label: 'Parameters', icon: '⬡'},
	// 	{id: 'files', label: 'Upload Files', icon: '⬢'},
	// 	{id: 'sanitize', label: 'Sanitize Cell Types', icon: '⬡'},
	// 	{id: 'review', label: 'Review & Submit', icon: '⬢'}
	// ];
	// const stepOrder: Step[] = ['params', 'files', 'sanitize', 'review'];
	// let submitted = $state({ success: false, message: '' });
	// let currentStep = $state<Step>('params');
	// let isSubmitting = $state(false);
	// let submitError = $state<string | null>(null);
	// let submitSuccess = $state(false);
	// let currentstate = $state({
	// 	caseStudyName: '',
	// 	organism: 'human' as const,
	// 	condition: '',
	// 	refCondition: '',
	// 	splitComplexes: false,
	// 	cccFile: null as File | null,
	// 	tflFile: null as File | null,
	// 	sanitizeCelltypes: false,
	// 	sanitizeReferenceFile: null as File | null
	// });
	// let errors: ValidationErrors = {};
	// let draggingFiles: 'ccc' | 'tf' | 'sanitize' | null = null;
	// function validateParams(): boolean {
	// 	errors = {};
	// 	if (!currentstate.caseStudyName.trim()) errors.caseStudyName = 'Required';
	// 	else if (!/^[a-zA-Z0-9_-]+$/.test(currentstate.caseStudyName))
	// 	errors.caseStudyName = 'Only letters, numbers, _ and - allowed';
	// 	if (!currentstate.condition.trim()) errors.condition = 'Required';
	// 	if (!currentstate.refCondition.trim()) errors.refCondition = 'Required';
	// 	if (currentstate.condition && currentstate.refCondition && currentstate.condition === currentstate.refCondition)
	// 	errors.refCondition = 'Must differ from condition';
	// 	return Object.keys(errors).length === 0;
	// }
	// function validateFiles(): boolean {
	// 	errors = {};
	// 	if (!currentstate.cccFile) errors.cccFile = 'CCC results file is required';
	// 	if (!currentstate.tflFile)  errors.tflFile  = 'TF activity file is required';
	// 	return Object.keys(errors).length === 0;
	// }
	// function validateCsv(file: File): Promise<string | null> {
	// 	return new Promise((resolve) => {
	// 	const reader = new FileReader();
	// 	reader.onload = (e) => {
	// 		const text = e.target?.result as string;
	// 		const firstLine = text.split('\n')[0];
	// 		if (!firstLine.includes(',') && !firstLine.includes('\t')) {
	// 		resolve('File does not appear to be a valid CSV');
	// 		} else {
	// 		resolve(null);
	// 		}
	// 	};
	// 	reader.onerror = () => resolve('Could not read file');
	// 	reader.readAsText(file.slice(0, 2000));
	// 	});
	// }
	// async function next() {
	// 	if (currentStep === 'params') {
	// 	if (!validateParams()) return;
	// 	currentStep = 'files';
	// 	} else if (currentStep === 'files') {
	// 	if (!validateFiles()) return;
	// 	currentStep = 'sanitize';
	// 	} else if (currentStep === 'sanitize') {
	// 	currentStep = 'review';
	// 	}
	// }
	// function back() {
	// 	const idx = stepOrder.indexOf(currentStep);
	// 	if (idx > 0) currentStep = stepOrder[idx - 1];
	// }
	// function goToStep(step: Step) {
	// 	const target = stepOrder.indexOf(step);
	// 	const current = stepOrder.indexOf(currentStep);
	// 	if (target < current) currentStep = step;
	// }
	// function handleFileInput(event: Event, field: 'cccFile' | 'tflFile' | 'sanitizeReferenceFile') {
	// 	const input = event.target as HTMLInputElement;
	// 	const file = input.files?.[0] || null;
	// 	currentstate = { ...currentstate, [field]: file };
	// 	if (field !== 'sanitizeReferenceFile') errors = { ...errors, [field]: undefined };
	// }
</script>

<fieldset>
	<legend>Case Study</legend>

	<!-- Case Study Selection -->
	<div class="form-check tooltip-wrapper">
		<input
			type="radio"
			value="als"
			checked={$selectedCaseStudy === 'ALS'}
			onchange={() => handleCaseStudyChange('ALS')}
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
			onchange={() => handleCaseStudyChange('FMD')}
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
		top: 100%;
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
