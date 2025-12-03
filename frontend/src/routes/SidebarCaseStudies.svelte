<!-- component for choosing between FMD and ALS case studies or upload data -->
<!--  STILL TO IMPLEMENT -->
<script lang="ts">
</script>

<fieldset>
	<!-- <legend>Case Studies</legend> -->
	<div class="form-check">
		<input
			class="form-check-input"
			type="radio"
			name="caseStudyOptions"
			id="fmd"
			value="fmd"
			checked
		/>
		<label class="form-check-label" for="fmd">FMD - Fibromuscular Dysplasia</label>
	</div>
	<div class="form-check disabled">
		<input
			class="form-check-input"
			type="radio"
			name="caseStudyOptions"
			id="als"
			value="als"
			disabled
		/>
		<label class="form-check-label" for="als">ALS - Amyotrophic Lateral Sclerosis</label>
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
</fieldset>
