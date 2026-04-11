import sodium from 'libsodium-wrappers-sumo';

async function hashArgon2(password, salt, iterations, memory) {
  const passwordBytes = sodium.from_string(password);
  const binaryString = atob(salt);
  const saltBytes = Uint8Array.from(binaryString, char => char.charCodeAt(0));
  const truncatedSalt = saltBytes.slice(0, 16);

  const hash = sodium.crypto_pwhash(
    32,
    passwordBytes,
    truncatedSalt,
    iterations,
    memory,
    sodium.crypto_pwhash_ALG_ARGON2ID13
  );

  return sodium.to_base64(hash, sodium.base64_variants.ORIGINAL);
}

self.onmessage = async function (e) {
  const { id, text, salt, iterations, memory } = e.data;

  try {
    await sodium.ready;
    const hash = await hashArgon2(text, salt, iterations, memory);
    self.postMessage({ id, success: true, result: hash });
  } catch (error) {
    self.postMessage({ id, success: false, error: error.message });
  }
};
