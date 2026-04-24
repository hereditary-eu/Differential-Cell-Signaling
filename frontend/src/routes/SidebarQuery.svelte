<script>
	import { selectedComparison } from '$lib/stores';
	const backend = import.meta.env.VITE_BACKEND_URL;
	async function findCycles() {
		try {
			const res = await fetch(`${backend}/api/cycles?comparison=${$selectedComparison}`);
			const cycles = await res.json();
			console.log('Cycles found:', cycles);
		} catch (err) {
			console.error('Error finding cycles:', err);
		}
	}
</script>

<button id="find-cycles-btn" type="button" class="btn btn-dark" on:click={findCycles} disabled>
	Find Cycles
</button>
<!-- <hr />
<button id="filter-net-stats-btn" type="button" class="btn btn-dark" disabled>
	Compute Network Science Metrics
</button> -->
<hr />
<button id="GEA-btn" type="button" class="btn btn-dark" disabled>
	Perform GO Enrichment Analysis
</button>
