<script lang="ts">
	import { onMount } from 'svelte';
	import { selectedCaseStudy, selectedComparison } from '$lib/stores';
	import { base } from '$app/paths';
	const backend = import.meta.env.VITE_BACKEND_URL ?? base;

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
	let { onsubmitted }: { onsubmitted?: (detail: { success: boolean; message: string }) => void } =
		$props();
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
		} else {
			selectedComparison.set('');
		}
	}

	// user defined case study
	type Step = 'params' | 'files' | 'sanitize' | 'review';
	interface ValidationErrors {
		caseStudyName?: string;
		condition?: string;
		refCondition?: string;
		cccFile?: string;
		tflFile?: string;
		sanitizeReferenceFile?: string;
	}
	const steps: { id: Step; label: string; icon: string }[] = [
		{ id: 'params', label: 'Parameters', icon: '⬡' },
		{ id: 'files', label: 'Upload Files', icon: '⬢' },
		{ id: 'sanitize', label: 'Sanitize Cell Types', icon: '⬡' },
		{ id: 'review', label: 'Review & Submit', icon: '⬢' }
	];
	const stepOrder: Step[] = ['params', 'files', 'sanitize', 'review'];
	// maps the dropzone's short "zone" id to the real key on currentstate
	const zoneKey = {
		ccc: 'cccFile',
		tf: 'tflFile',
		sanitize: 'sanitizeReferenceFile'
	} as const;
	type Zone = keyof typeof zoneKey;

	let currentStep = $state<Step>('params');
	let isSubmitting = $state(false);
	let submitError = $state<string | null>(null);
	let submitSuccess = $state(false);
	let currentstate = $state({
		caseStudyName: '',
		organism: 'human' as 'human' | 'mouse',
		condition: '',
		refCondition: '',
		splitComplexes: false,
		cccFile: null as File | null,
		tflFile: null as File | null,
		sanitizeCelltypes: false,
		sanitizeReferenceFile: null as File | null
	});
	let errors = $state<ValidationErrors>({});
	let draggingOver = $state<Zone | null>(null);

	// validation functions
	function validateParams(): boolean {
		errors = {};
		if (!currentstate.caseStudyName.trim()) errors.caseStudyName = 'Required';
		else if (!/^[a-zA-Z0-9_-]+$/.test(currentstate.caseStudyName))
			errors.caseStudyName = 'Only letters, numbers, _ and - allowed';
		if (!currentstate.condition.trim()) errors.condition = 'Required';
		if (!currentstate.refCondition.trim()) errors.refCondition = 'Required';
		if (
			currentstate.condition &&
			currentstate.refCondition &&
			currentstate.condition === currentstate.refCondition
		)
			errors.refCondition = 'Must differ from condition';
		return Object.keys(errors).length === 0;
	}
	function validateFiles(): boolean {
		errors = { ...errors, cccFile: undefined, tflFile: undefined };
		if (!currentstate.cccFile) errors.cccFile = 'CCC results file is required';
		if (!currentstate.tflFile) errors.tflFile = 'TF activity file is required';
		return !errors.cccFile && !errors.tflFile; // ← checks actual values
	}
	function validateSanitize(): boolean {
		errors = { ...errors, sanitizeReferenceFile: undefined };
		if (currentstate.sanitizeCelltypes && !currentstate.sanitizeReferenceFile) {
			errors = {
				...errors,
				sanitizeReferenceFile: 'Upload a reference file or uncheck sanitization'
			};
			return false;
		}
		return true;
	}
	function validateCsv(file: File): Promise<string | null> {
		return new Promise((resolve) => {
			const reader = new FileReader();
			reader.onload = (e) => {
				const text = e.target?.result as string;
				const firstLine = text.split('\n')[0];
				if (!firstLine.includes(',') && !firstLine.includes('\t')) {
					resolve('File does not appear to be a valid CSV');
				} else {
					resolve(null);
				}
			};
			reader.onerror = () => resolve('Could not read file');
			reader.readAsText(file.slice(0, 2000));
		});
	}
	// moving steps functions
	async function next() {
		if (currentStep === 'params') {
			if (!validateParams()) return;
			currentStep = 'files';
		} else if (currentStep === 'files') {
			if (!validateFiles()) return;
			currentStep = 'sanitize';
		} else if (currentStep === 'sanitize') {
			if (!validateSanitize()) return;
			currentStep = 'review';
		}
	}
	function back() {
		const idx = stepOrder.indexOf(currentStep);
		if (idx > 0) currentStep = stepOrder[idx - 1];
	}
	function goToStep(step: Step) {
		const target = stepOrder.indexOf(step);
		const current = stepOrder.indexOf(currentStep);
		if (target < current) currentStep = step;
	}
	// files upload functions
	async function setFile(zone: Zone, file: File | null) {
		const key = zoneKey[zone];
		currentstate = { ...currentstate, [key]: file };
		errors = { ...errors, [key]: undefined };
		if (file) {
			const err = await validateCsv(file);
			if (err) errors = { ...errors, [key]: err };
		}
	}
	function handleFileInput(event: Event, zone: Zone) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0] ?? null;
		setFile(zone, file);
	}

	function handleDrop(event: DragEvent, zone: Zone) {
		event.preventDefault();
		draggingOver = null;
		const file = event.dataTransfer?.files?.[0] ?? null;
		if (file && file.name.endsWith('.csv')) {
			setFile(zone, file);
		}
	}
	function handleDragOver(event: DragEvent, zone: Zone) {
		event.preventDefault();
		draggingOver = zone;
	}
	function removeFile(zone: Zone) {
		const key = zoneKey[zone];
		currentstate = { ...currentstate, [key]: null };
	}
	async function pollIngestion(jobId: string) {
		while (true) {
			await new Promise((r) => setTimeout(r, 2000));
			const res = await fetch(`${backend}/api/ingestion_status/${jobId}`);
			if (!res.ok) throw new Error('Could not reach status endpoint');
			const { status, error } = await res.json();
			if (status === 'done') {
				submitSuccess = true;
				selectedCaseStudy.set(currentstate.caseStudyName);
				selectedComparison.set(`${currentstate.condition}_vs_${currentstate.refCondition}`);
				onsubmitted?.({ success: true, message: 'Case study uploaded successfully' });
				return;
			}
			if (status === 'failed') {
				throw new Error(`Ingestion failed:\n${error}`);
			}
			// still 'pending' or 'running' — keep polling
		}
	}
	async function submit() {
		isSubmitting = true;
		submitError = null;

		try {
			const formData = new FormData();
			formData.append('caseStudyName', currentstate.caseStudyName);
			formData.append('organism', currentstate.organism);
			formData.append('condition', currentstate.condition);
			formData.append('refCondition', currentstate.refCondition);
			formData.append('splitComplexes', String(currentstate.splitComplexes));
			if (currentstate.cccFile) formData.append('cccFile', currentstate.cccFile);
			if (currentstate.tflFile) formData.append('tflFile', currentstate.tflFile);
			if (currentstate.sanitizeCelltypes && currentstate.sanitizeReferenceFile) {
				formData.append('sanitizeCelltypes', String(currentstate.sanitizeCelltypes));
				formData.append('sanitizeReferenceFile', currentstate.sanitizeReferenceFile);
			}
			const response = await fetch(`${backend}/api/upload_case_study`, {
				method: 'POST',
				body: formData
			});
			if (!response.ok) {
				const data = await response.json().catch(() => ({}));
				throw new Error(data.detail ?? `Server error: ${response.status}`);
			}
			const { jobId } = await response.json();
			await pollIngestion(jobId); // poll every 2sec until job done or failed
		} catch (e: any) {
			submitError = e.message;
		} finally {
			isSubmitting = false;
		}
	}

	function reset() {
		currentstate = {
			caseStudyName: '',
			organism: 'human',
			condition: '',
			refCondition: '',
			splitComplexes: false,
			cccFile: null,
			tflFile: null,
			sanitizeCelltypes: false,
			sanitizeReferenceFile: null
		};
		errors = {};
		currentStep = 'params';
		submitError = null;
		submitSuccess = false;
	}

	function formatBytes(bytes: number): string {
		if (bytes < 1024) return bytes + 'B';
		if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB';
		return (bytes / (1024 * 1024)).toFixed(1) + 'MB';
	}
	let stepIndex = $derived(stepOrder.indexOf(currentStep));
	let comparisonLabel = $derived(
		currentstate.condition && currentstate.refCondition
			? `${currentstate.condition} vs ${currentstate.refCondition}`
			: 'Select conditions to compare'
	);
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

	<div class="form-check">
		<input
			class="form-check-input"
			type="radio"
			name="caseStudyOptions"
			id="upload"
			value="upload"
			checked={$selectedCaseStudy === 'upload'}
			onchange={() => handleCaseStudyChange('')}
		/>
		<label for="upload" class="form-check-label">Upload your own data</label>
	</div>
	<hr />

	{#if $selectedCaseStudy === 'FMD'}
		<div class="form-check tooltip-wrapper">
			<input type="radio" value="Ko_vs_Wt" bind:group={$selectedComparison} id="ko_vs_wt" />
			<label for="ko_vs_wt">KO vs WT</label>
			<div class="tooltip">
				{tooltips.Ko_vs_Wt}
			</div>
		</div>
	{:else if $selectedCaseStudy === 'ALS'}
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
	{:else}
		<div class="upload-panel">
			<header class="h6">Upload your own case study</header>

			<!-- step indicator -->
			<!-- <nav class="stepper" aria-label="Upload Step">
				{#each steps as step, i}
					<button
						type="button"
						class="step-item"
						class:active={currentStep === step.id}
						class:done={stepOrder.indexOf(step.id) < stepIndex}
						class:clickable={stepOrder.indexOf(step.id) < stepIndex}
						onclick={() => goToStep(step.id)}
						disabled={stepOrder.indexOf(step.id) >= stepIndex}
						aria-current={currentStep === step.id ? 'step' : undefined}
					>
						<span class="step-icon">{step.icon}</span>
						<span class="step-num">{i + 1}</span>
						<span class="step-label">{step.label}</span>
					</button>
					{#if i < steps.length - 1}
						<div class="step-connector" class:filled={stepIndex > i}></div>
					{/if}
				{/each}
			</nav> -->

			<!-- parameters' setting -->
			{#if currentStep === 'params'}
				<div class="step-content" aria-label="Parameters">
					<span>Step 1</span>
					<div class="field-grid">
						<div class="field full">
							<label for="csname">Case Study Name</label>
							<input
								id="csname"
								type="text"
								placeholder="e.g. MyDisease2024"
								bind:value={currentstate.caseStudyName}
								class:error={!!errors.caseStudyName}
								autocomplete="off"
								spellcheck="false"
							/>
							{#if errors.caseStudyName}
								<span class="field-error">{errors.caseStudyName}</span>
							{:else}
								<span class="field-hint">Alphanumeric, underscores, hyphens only</span>
							{/if}
						</div>

						<div class="field full">
							<label for="cond">Condition <span class="label-tag">case</span></label>
							<input
								id="cond"
								type="text"
								placeholder="e.g. Disease"
								bind:value={currentstate.condition}
								class:error={!!errors.condition}
							/>
							{#if errors.condition}
								<span class="field-error">{errors.condition}</span>
							{/if}
						</div>
						<div class="field full">
							<label for="refcond">Condition <span class="label-tag">reference</span></label>
							<input
								id="refcond"
								type="text"
								placeholder="e.g. Control"
								bind:value={currentstate.refCondition}
								class:error={!!errors.refCondition}
							/>
							{#if errors.refCondition}
								<span class="field-error">{errors.refCondition}</span>
							{/if}
						</div>

						{#if currentstate.condition && currentstate.refCondition && !errors.condition && !errors.refCondition}
							<div class="comparison-preview full">
								<span class="comparison-label">Comparison</span>
								<span class="comparison-value">{comparisonLabel}</span>
							</div>
						{/if}

						<div class="field full">
							<label for="org">Organism</label>
							<div class="select-wrap">
								<select id="org" bind:value={currentstate.organism}>
									<option value="human">Human</option>
									<option value="mouse">Mouse</option>
								</select>
							</div>
						</div>

						<div class="field full toggle-field">
							<span class="toggle-label">Split complexes</span>
							<label for="splitComplexes" class="toggle" aria-label="Split complexes toggle">
								<input
									type="checkbox"
									bind:checked={currentstate.splitComplexes}
									id="splitComplexes"
								/>
							</label>
						</div>
					</div>

					<div class="step-actions justify-end">
						<button type="button" class="btn btn-primary" onclick={next}>Next →</button>
					</div>
				</div>
				<!-- END PARAMETERS -->

				<!-- INPUT FILES -->
			{:else if currentStep === 'files'}
				<div class="step-content" aria-label="Upload Files">
					<span>Step 2</span>
					<h3>Upload your case study CSV files</h3>

					<!-- <div class="dropzone-grid"> -->
					<!-- CCC file -->
					<div
						class="dropzone"
						class:dragging={draggingOver === 'ccc'}
						class:has-file={!!currentstate.cccFile}
						class:has-error={!!errors.cccFile}
						ondragover={(e) => handleDragOver(e, 'ccc')}
						ondragleave={() => (draggingOver = null)}
						ondrop={(e) => handleDrop(e, 'ccc')}
						role="region"
						aria-label="CCC file upload"
					>
						{#if currentstate.cccFile}
							<div class="file-info">
								<span class="file-icon">◈</span>
								<div class="file-meta">
									<span class="file-name">{currentstate.cccFile.name}</span>
									<span class="file-size">{formatBytes(currentstate.cccFile.size)}</span>
								</div>
								<button
									class="remove-btn"
									onclick={() => removeFile('ccc')}
									aria-label="Remove CCC file">✕</button
								>
							</div>
						{:else}
							<div class="dropzone-inner">
								<span class="drop-icon">⊕</span>
								<p class="drop-title">CCC Results</p>
								<p class="drop-hint">
									ligand, receptor, sender, receiver,<br />S_intra, pvalue_adj_S_inter,<br
									/>S_inter_{'{cond}'}, S_inter_{'{ref}'}
								</p>
								<label for="cccFile" class="file-btn">
									Browse
									<input
										id="cccFile"
										type="file"
										accept=".csv"
										onchange={(e) => handleFileInput(e, 'ccc')}
									/>
								</label>
							</div>
						{/if}
						{#if errors.cccFile}
							<span class="field-error below">{errors.cccFile}</span>
						{/if}
					</div>
					<!-- TF file -->
					<div
						class="dropzone"
						class:dragging={draggingOver === 'tf'}
						class:has-file={!!currentstate.tflFile}
						class:has-error={!!errors.tflFile}
						ondragover={(e) => handleDragOver(e, 'tf')}
						ondragleave={() => (draggingOver = null)}
						ondrop={(e) => handleDrop(e, 'tf')}
						role="region"
						aria-label="TF file upload"
					>
						{#if currentstate.tflFile}
							<div class="file-info">
								<span class="file-icon">◈</span>
								<div class="file-meta">
									<span class="file-name">{currentstate.tflFile.name}</span>
									<span class="file-size">{formatBytes(currentstate.tflFile.size)}</span>
								</div>
								<button
									class="remove-btn"
									onclick={() => removeFile('tf')}
									aria-label="Remove TF file">✕</button
								>
							</div>
						{:else}
							<div class="dropzone-inner">
								<span class="drop-icon">⊕</span>
								<p class="drop-title">TF Results</p>
								<p class="drop-hint">TF, statistic, padj, log2FC, celltype</p>
								<label for="tfFile" class="file-btn">
									Browse
									<input
										id="tfFile"
										type="file"
										accept=".csv"
										onchange={(e) => handleFileInput(e, 'tf')}
									/>
								</label>
							</div>
						{/if}
						{#if errors.tflFile}
							<span class="field-error below">{errors.tflFile}</span>
						{/if}
						<!-- </div> -->
					</div>

					<div class="step-actions">
						<button type="button" class="btn btn-outline-secondary" onclick={back}>← Back</button>
						<button type="button" class="btn btn-primary" onclick={next}>Next →</button>
					</div>
				</div>
			{:else if currentStep === 'sanitize'}
				<div class="step-content">
					<span>Step 3</span>
					<h2>Sanitize Cell Types Names (optional)</h2>
					<p>
						If cell types have long names in your results, provide a mapping of the original names
						to the shortened names for graphical purposes.
					</p>
					<label for="sanitize">
						<input id="sanitize" type="checkbox" bind:checked={currentstate.sanitizeCelltypes} />
						I want to sanitize cell type names
					</label>

					{#if currentstate.sanitizeCelltypes}
						<div
							class="dropzone sanitize"
							class:dragging={draggingOver === 'sanitize'}
							class:has-file={!!currentstate.sanitizeReferenceFile}
							class:has-error={!!errors.sanitizeReferenceFile}
							ondragover={(e) => handleDragOver(e, 'sanitize')}
							ondragleave={() => (draggingOver = null)}
							ondrop={(e) => handleDrop(e, 'sanitize')}
							role="region"
							aria-label="Cell type sanitization file upload"
						>
							{#if currentstate.sanitizeReferenceFile}
								<div class="file-info">
									<span class="file-icon">◈</span>
									<div class="file-meta">
										<span class="file-name">{currentstate.sanitizeReferenceFile.name}</span>
										<span class="file-size"
											>{formatBytes(currentstate.sanitizeReferenceFile.size)}</span
										>
									</div>
									<button
										class="remove-btn"
										onclick={() => removeFile('sanitize')}
										aria-label="Remove sanitization file">✕</button
									>
								</div>
							{:else}
								<div class="dropzone-inner">
									<span class="drop-icon">⊕</span>
									<p class="drop-title">Sanitization Reference File</p>
									<p class="drop-hint">
										Required columns: <code>oldName</code>, <code>newName</code>
									</p>
									<label for="sanitizeReferenceFile" class="file-btn">
										Browse
										<input
											id="sanitizeReferenceFile"
											type="file"
											accept=".csv"
											onchange={(e) => handleFileInput(e, 'sanitize')}
										/>
									</label>
								</div>
							{/if}
						</div>
						{#if errors.sanitizeReferenceFile}
							<span class="field-error below">{errors.sanitizeReferenceFile}</span>
						{/if}
					{/if}

					<div class="step-actions">
						<button type="button" class="btn btn-outline-secondary" onclick={back}>← Back</button>
						<button type="button" class="btn btn-primary" onclick={next}>Next →</button>
					</div>
				</div>

				<!-- REVIEW AND SUBMIT -->
			{:else if currentStep === 'review'}
				<div class="step-content" aria-label="Review and Submit">
					<span>Step 4</span>
					<h2>Review your submission</h2>
					{#if submitSuccess}
						<div class="success-state">
							<div class="success-icon">✓</div>
							<h3>Upload successful</h3>
							<p>
								Your case study <strong>{currentstate.caseStudyName}</strong> has been ingested and will
								be available shortly.
							</p>
							<button class="btn btn-primary" onclick={reset}>Upload another</button>
						</div>
					{:else}
						<dl>
							<dt>Case Study Name</dt>
							<dd>{currentstate.caseStudyName}</dd>
							<dt>Organism</dt>
							<dd>{currentstate.organism}</dd>
							<dt>Comparison</dt>
							<dd>{comparisonLabel}</dd>
							<dt>Split Complexes</dt>
							<dd>{currentstate.splitComplexes ? 'Yes' : 'No'}</dd>
							<dt>CCC File</dt>
							<dd>{currentstate.cccFile ? currentstate.cccFile.name : 'No file uploaded'}</dd>
							<dt>TF Activity File</dt>
							<dd>{currentstate.tflFile ? currentstate.tflFile.name : 'No file uploaded'}</dd>
							{#if currentstate.sanitizeCelltypes}
								<dt>Sanitize Cell Types</dt>
								<dd>Yes</dd>
								<dt>Sanitization Reference File</dt>
								<dd>
									{currentstate.sanitizeReferenceFile
										? currentstate.sanitizeReferenceFile.name
										: 'No file uploaded'}
								</dd>
							{:else}
								<dt>Sanitize Cell Types</dt>
								<dd>No</dd>
							{/if}
						</dl>
						{#if submitError}
							<div class="error-banner" role="alert">
								<span>{submitError}</span>
							</div>
						{/if}

						<div class="step-actions">
							<button
								type="button"
								class="btn btn-outline-secondary"
								onclick={back}
								disabled={isSubmitting}>← Back</button
							>
							<button
								type="button"
								class="btn btn-primary"
								onclick={submit}
								disabled={isSubmitting}
							>
								{#if isSubmitting}
									<span class="spinner"></span> Processing… this may take a minute
								{:else}
									Submit case study
								{/if}
							</button>
						</div>
					{/if}
				</div>

				<!-- end if within custom upload -->
			{/if}
		</div>

		<!-- external if for case study top level check boxes -->
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
		z-index: 5;
	}

	.tooltip-wrapper:hover .tooltip {
		opacity: 1;
	}

	/* ---------------------------------------------------------------- *
	 * Upload wizard — styled with Bootstrap/Bootswatch CSS variables so
	 * it automatically follows the Lux theme (and any future theme swap).
	 * ---------------------------------------------------------------- */
	.upload-panel {
		margin-top: 1rem;
	}

	/* .stepper {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		margin: 1rem 0 1.5rem;
		flex-wrap: wrap;
	}
	.step-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.15rem;
		min-width: 84px;
		padding: 0.5rem 0.25rem;
		background: none;
		border: none;
		border-radius: var(--bs-border-radius, 0.375rem);
		font-size: 0.75rem;
		color: var(--bs-secondary-color, #6c757d);
		opacity: 0.55;
		cursor: not-allowed;
		transition: opacity 0.15s ease, color 0.15s ease, background 0.15s ease;
	} */
	/* .step-item.clickable {
		opacity: 1;
		cursor: pointer;
	}
	.step-item.clickable:hover {
		background: var(--bs-tertiary-bg, #f4f4f4);
	}
	.step-item.done {
		opacity: 1;
		color: var(--bs-success, #198754);
	}
	.step-item.active {
		opacity: 1;
		color: var(--bs-primary, #6610f2);
		font-weight: 600;
	}
	.step-icon {
		font-size: 1.15rem;
		line-height: 1;
	}
	.step-num {
		display: none;
	}
	.step-label {
		white-space: nowrap;
	} */
	/* .step-connector {
		flex: 1 1 auto;
		min-width: 4px;
		height: 2px;
		background: var(--bs-border-color, #dee2e6);
		margin: 0 0.15rem;
	}
	.step-connector.filled {
		background: var(--bs-primary, #6610f2);
	} */

	.step-content {
		padding-top: 0.25rem;
	}
	.step-content > span {
		display: inline-block;
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--bs-secondary-color, #6c757d);
		margin-bottom: 0.25rem;
	}

	.field-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		margin-top: 0.75rem;
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.field.full {
		grid-column: 1 / -1;
	}
	.field label {
		font-weight: 600;
		font-size: 0.85rem;
	}
	.label-tag {
		font-weight: 400;
		font-size: 0.68rem;
		text-transform: uppercase;
		color: var(--bs-secondary-color, #6c757d);
		margin-left: 0.25rem;
	}
	.field input[type='text'],
	.select-wrap select {
		border: 1px solid var(--bs-border-color, #dee2e6);
		border-radius: var(--bs-border-radius, 0.375rem);
		padding: 0.5rem 0.65rem;
		background: var(--bs-body-bg, #fff);
		color: var(--bs-body-color, #212529);
		width: 100%;
	}
	.field input[type='text']:focus,
	.select-wrap select:focus {
		outline: none;
		border-color: var(--bs-primary, #6610f2);
		box-shadow: 0 0 0 0.2rem rgba(var(--bs-primary-rgb, 102, 16, 242), 0.2);
	}
	.field input.error {
		border-color: var(--bs-danger, #dc3545);
	}
	.field-error {
		color: var(--bs-danger, #dc3545);
		font-size: 0.8rem;
	}
	.field-error.below {
		display: block;
		margin-top: 0.5rem;
	}
	.field-hint {
		font-size: 0.78rem;
		color: var(--bs-secondary-color, #6c757d);
	}

	.comparison-preview {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		background: var(--bs-tertiary-bg, #f4f4f4);
		border-radius: var(--bs-border-radius, 0.375rem);
		padding: 0.5rem 0.75rem;
	}
	.comparison-label {
		font-size: 0.72rem;
		text-transform: uppercase;
		color: var(--bs-secondary-color, #6c757d);
	}
	.comparison-value {
		font-weight: 600;
	}

	.toggle-field {
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
	}
	.toggle input[type='checkbox'] {
		width: 40px;
		height: 22px;
		accent-color: var(--bs-primary, #6610f2);
		cursor: pointer;
	}

	/* .dropzone-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		margin-top: 1rem;
	} */
	.dropzone {
		border: 2px dashed var(--bs-border-color, #dee2e6);
		border-radius: var(--bs-border-radius, 0.375rem);
		padding: 1.25rem;
		text-align: center;
		background: var(--bs-body-bg, #fff);
		transition:
			border-color 0.15s ease,
			background 0.15s ease;
	}
	.dropzone.dragging {
		border-color: var(--bs-primary, #6610f2);
		background: var(--bs-tertiary-bg, #f4f4f4);
	}
	.dropzone.has-file {
		border-style: solid;
		border-color: var(--bs-success, #198754);
		background: var(--bs-tertiary-bg, #f4f4f4);
	}
	.dropzone.has-error {
		border-color: var(--bs-danger, #dc3545);
	}
	.dropzone.sanitize {
		margin-top: 1rem;
	}
	.dropzone-inner {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.35rem;
	}
	.drop-icon {
		font-size: 1.75rem;
		color: var(--bs-primary, #6610f2);
	}
	.drop-title {
		font-weight: 600;
		margin: 0;
	}
	.drop-hint {
		font-size: 0.78rem;
		line-height: 1.4;
		color: var(--bs-secondary-color, #6c757d);
		margin: 0;
	}
	.file-btn {
		display: inline-block;
		margin-top: 0.5rem;
		padding: 0.4rem 1rem;
		border-radius: var(--bs-border-radius, 0.375rem);
		background: var(--bs-primary, #6610f2);
		color: #fff;
		font-size: 0.85rem;
		cursor: pointer;
	}
	.file-btn:hover {
		filter: brightness(0.93);
	}
	.file-btn input[type='file'] {
		display: none;
	}

	.file-info {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}
	.file-icon {
		font-size: 1.4rem;
		color: var(--bs-success, #198754);
	}
	.file-meta {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-width: 0;
		text-align: left;
	}
	.file-name {
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.file-size {
		font-size: 0.78rem;
		color: var(--bs-secondary-color, #6c757d);
	}
	.remove-btn {
		border: none;
		background: none;
		color: var(--bs-danger, #dc3545);
		font-size: 1rem;
		line-height: 1;
		padding: 0.25rem;
		cursor: pointer;
	}

	.step-actions {
		display: flex;
		justify-content: space-between;
		margin-top: 1.5rem;
	}
	.step-actions.justify-end {
		justify-content: flex-end;
	}

	dl {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.4rem 1rem;
		margin-top: 1rem;
	}
	dt {
		font-weight: 600;
		color: var(--bs-secondary-color, #6c757d);
	}
	dd {
		margin: 0;
	}

	.error-banner {
		margin-top: 1rem;
		padding: 0.6rem 0.9rem;
		border-radius: var(--bs-border-radius, 0.375rem);
		background: rgba(var(--bs-danger-rgb, 220, 53, 69), 0.1);
		border: 1px solid rgba(var(--bs-danger-rgb, 220, 53, 69), 0.3);
		color: var(--bs-danger, #dc3545);
	}

	.success-state {
		text-align: center;
		padding: 1.5rem 0;
	}
	.success-icon {
		width: 48px;
		height: 48px;
		margin: 0 auto 1rem;
		border-radius: 50%;
		background: var(--bs-success, #198754);
		color: #fff;
		font-size: 1.4rem;
		line-height: 48px;
	}

	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		margin-right: 0.4rem;
		vertical-align: middle;
		border: 2px solid rgba(255, 255, 255, 0.5);
		border-top-color: #fff;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* @media (max-width: 640px) {
		.field-grid
		.dropzone-grid {
			grid-template-columns: 1fr;
		}
		.step-label {
			display: none;
		}
	} 
	*/
</style>
