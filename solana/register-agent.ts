/**
 * Metaplex Agent Registration Script
 *
 * Registers the Frontier Tower Concierge agent on Solana via the
 * Metaplex Agent Registry. Creates an MPL Core asset with an
 * AgentIdentity plugin.
 *
 * Usage:
 *   npx tsx register-agent.ts
 *
 * Prerequisites:
 *   - Solana CLI configured with a funded keypair
 *   - Agent registration JSON uploaded to Arweave/IPFS
 */

import { createUmi } from '@metaplex-foundation/umi-bundle-defaults';
import { keypairIdentity, generateSigner } from '@metaplex-foundation/umi';
import {
  createCollectionV1,
  createV1,
} from '@metaplex-foundation/mpl-core';
import { registerIdentityV1 } from '@metaplex-foundation/mpl-agent-registry/dist/src/generated/identity';
import { mplAgentIdentity } from '@metaplex-foundation/mpl-agent-registry';

const CLUSTER_URL = process.env.SOLANA_RPC_URL || 'https://api.devnet.solana.com';
const REGISTRATION_URI = process.env.AGENT_REGISTRATION_URI || '';

async function main() {
  if (!REGISTRATION_URI) {
    console.error('Set AGENT_REGISTRATION_URI to the hosted agent-registration.json URL');
    process.exit(1);
  }

  console.log('Connecting to Solana cluster:', CLUSTER_URL);
  const umi = createUmi(CLUSTER_URL);

  // Load keypair from Solana CLI default (~/.config/solana/id.json)
  const fs = await import('fs');
  const path = await import('path');
  const os = await import('os');
  const keypairPath = path.join(os.homedir(), '.config', 'solana', 'id.json');
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, 'utf-8'));
  const keypair = umi.eddsa.createKeypairFromSecretKey(new Uint8Array(keypairData));
  umi.use(keypairIdentity(keypair));
  umi.use(mplAgentIdentity());

  console.log('Wallet:', keypair.publicKey.toString());

  // 1. Create a collection for the agent
  const collectionSigner = generateSigner(umi);
  console.log('Creating collection...');
  await createCollectionV1(umi, {
    collection: collectionSigner,
    name: 'Frontier Tower Agents',
    uri: REGISTRATION_URI,
  }).sendAndConfirm(umi);
  console.log('Collection:', collectionSigner.publicKey.toString());

  // 2. Create the agent asset
  const assetSigner = generateSigner(umi);
  console.log('Creating agent asset...');
  await createV1(umi, {
    asset: assetSigner,
    collection: collectionSigner.publicKey,
    name: 'Frontier Tower Concierge',
    uri: REGISTRATION_URI,
    plugins: [],
  }).sendAndConfirm(umi);
  console.log('Agent asset:', assetSigner.publicKey.toString());

  // 3. Register the agent identity
  console.log('Registering agent identity...');
  await registerIdentityV1(umi, {
    asset: assetSigner.publicKey,
    collection: collectionSigner.publicKey,
    agentRegistrationUri: REGISTRATION_URI,
  }).sendAndConfirm(umi);

  console.log('\nAgent registered successfully!');
  console.log('Asset public key:', assetSigner.publicKey.toString());
  console.log('Collection public key:', collectionSigner.publicKey.toString());
  console.log('Registration URI:', REGISTRATION_URI);
  console.log(
    '\nView on Solana Explorer:',
    `https://explorer.solana.com/address/${assetSigner.publicKey.toString()}?cluster=devnet`,
  );
}

main().catch(console.error);
