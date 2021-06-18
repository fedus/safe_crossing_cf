const functions = require('firebase-functions');
const admin = require('firebase-admin');

admin.initializeApp();

const db = admin.firestore();

const nodeIdToFirestoreId = (nodeId) => nodeId.split('/')[1];

exports.initializeUser = functions
    .region('europe-west1')
    .https
    .onCall(async (data, context) => {
      const {userUuid} = data;

      const userDoc = await db.collection('users').doc(userUuid).get();

      if (userDoc.exists && userDoc.get('initialized')) {
        return Promise.resolve('USER_ALREADY_INITIALIZED');
      }

      const allCrossings = await db.collection('crossings').get();

      let batch = db.batch();
      let index = 0;

      functions.logger.log(`Initializing user ${userUuid}`);

      for (const currentCrossing of allCrossings.docs) {
        functions.logger.log(`Working off ${currentCrossing.id}`);
        batch.update(currentCrossing.ref, {
          'unseenBy': admin.firestore.FieldValue.arrayUnion(userUuid),
        });

        if ((index + 1) % 498 == 0) {
          functions.logger.log(`Committing intermediate batch at index $index`);
          await batch.commit();
          batch = db.batch();
        }

        index++;
      }

      batch.set(userDoc.ref, {initialized: true}, {merge: true});

      functions.logger.log('Committing user eligibility ...');
      await batch.commit();

      return Promise.resolve('USER_INITIALIZED');
    });

exports.vote = functions
    .region('europe-west1')
    .https
    .onCall((data, context) => {
      const {userUuid, crossingNodeId, vote} = data;

      const voteEnumIndextoString = ['CANT_SAY', 'OK', 'PARKING_CLOSE'];
      const voteEnumIndextoFirestoreProperty = [
        'votesNotSure',
        'votesOk',
        'votesTooClose',
      ];
      const metaVoteEnumIndextoFirestoreProperty = [
        'votesNotSure',
        'votesOk',
        'votesTooClose',
        'votesTie',
      ];

      functions
          .logger
          .log(
              `User ${userUuid} voting for \
              ${crossingNodeId} with ${vote} \
              (${voteEnumIndextoString[vote]})`,
          );

      const crossingRef = db.collection('crossings')
          .doc(crossingNodeId.split('/')[1]);

      const voteRef = crossingRef
          .collection('votes')
          .doc(userUuid);

      const userDoc = db.collection('users').doc(userUuid);

      const metaDoc = db.collection('meta').doc('meta');

      return db.runTransaction(async (transaction) => {
        const voteSnapshot = await voteRef.get();
        const crossingSnapshot = await crossingRef.get();

        const crossingData = crossingSnapshot.data();

        const totalVotesForCrossing = crossingData.votesTotal;

        const currentResult = crossingData.currentResult;

        let newResult;

        if (voteSnapshot.exists) {
          functions.logger.log(`User ${userUuid} has already voted`);
          const existingVote = voteSnapshot.get('vote');

          if (existingVote != vote) {
            functions
                .logger
                .log(`User ${userUuid} wants to change their vote`);

            const parsedVotes = {
              votesNotSure: (
                vote == 0 ?
                crossingData.votesNotSure + 1 :
                (existingVote == 0 ?
                  crossingData.votesNotSure - 1 :
                  crossingData.votesNotSure)),
              votesOk: (
                vote == 1 ?
                crossingData.votesOk + 1 :
                (existingVote == 1 ?
                  crossingData.votesOk - 1 :
                  crossingData.votesOk)),
              votesTooClose: (
                vote == 2 ?
                crossingData.votesTooClose + 1 :
                (existingVote == 2 ?
                  crossingData.votesTooClose - 1 :
                  crossingData.votesTooClose)),
            };

            if (parsedVotes.votesNotSure > parsedVotes.votesOk &&
              parsedVotes.votesNotSure > parsedVotes.votesTooClose) {
              newResult = 0;
            } else if (parsedVotes.votesOk > parsedVotes.votesNotSure &&
              parsedVotes.votesOk > parsedVotes.votesTooClose) {
              newResult = 1;
            } else if (parsedVotes.votesTooClose > parsedVotes.votesOk &&
              parsedVotes.votesTooClose > parsedVotes.votesNotSure) {
              newResult = 2;
            } else {
              newResult = 3;
            }

            functions
                .logger
                .log(`Result, old: ${currentResult}, new ${newResult}`);

            transaction.update(crossingRef, {
              [voteEnumIndextoFirestoreProperty[existingVote]]: admin
                  .firestore
                  .FieldValue
                  .increment(-1),
              [voteEnumIndextoFirestoreProperty[vote]]: admin
                  .firestore
                  .FieldValue
                  .increment(1),
              currentResult: newResult,
            });
          }
        } else {
          functions
              .logger
              .log(`User ${userUuid} is casting their first vote`);

          transaction.update(userDoc, {
            'totalVotesCast': admin.firestore.FieldValue.increment(1),
          });

          const parsedVotes = {
            votesNotSure: (
              vote == 0 ?
              crossingData.votesNotSure + 1 :
              crossingData.votesNotSure),
            votesOk: (
              vote == 1 ?
              crossingData.votesOk + 1 :
              crossingData.votesOk),
            votesTooClose: (
              vote == 2 ?
              crossingData.votesTooClose + 1 :
              crossingData.votesTooClose),
          };

          if (parsedVotes.votesNotSure > parsedVotes.votesOk &&
            parsedVotes.votesNotSure > parsedVotes.votesTooClose) {
            newResult = 0;
          } else if (parsedVotes.votesOk > parsedVotes.votesNotSure &&
            parsedVotes.votesOk > parsedVotes.votesTooClose) {
            newResult = 1;
          } else if (parsedVotes.votesTooClose > parsedVotes.votesOk &&
            parsedVotes.votesTooClose > parsedVotes.votesNotSure) {
            newResult = 2;
          } else {
            newResult = 3;
          }

          functions
              .logger
              .log(`Result, old: ${currentResult}, new ${newResult}`);

          transaction.update(crossingRef, {
            [voteEnumIndextoFirestoreProperty[vote]]: admin
                .firestore
                .FieldValue
                .increment(1),
            votesTotal: admin.firestore.FieldValue.increment(1),
            unseenBy: admin.firestore.FieldValue.arrayRemove(userUuid),
            currentResult: newResult,
          });

          if (totalVotesForCrossing == 4) { // 5th vote was just cast
            functions
                .logger
                .log(`5th vote cast, incrementing \
                    ${metaVoteEnumIndextoFirestoreProperty[newResult]}`);

            transaction.update(metaDoc, {
              crossingsWithEnoughVotes: admin.firestore.FieldValue.increment(1),
              [metaVoteEnumIndextoFirestoreProperty[newResult]]: admin
                  .firestore
                  .FieldValue
                  .increment(1),
            });
          }
        }

        if (totalVotesForCrossing > 4 &&
          newResult && newResult != currentResult) {
          functions
              .logger
              .log(`> 5th vote cast, incrementing \
                  ${metaVoteEnumIndextoFirestoreProperty[newResult]} \
                  and decrementing \
                  ${metaVoteEnumIndextoFirestoreProperty[currentResult]}`);

          transaction.update(metaDoc, {
            [metaVoteEnumIndextoFirestoreProperty[currentResult]]: admin
                .firestore
                .FieldValue
                .increment(-1),
            [metaVoteEnumIndextoFirestoreProperty[newResult]]: admin
                .firestore
                .FieldValue
                .increment(1),
          });
        }

        functions
            .logger
            .log('Persisting user\'s decision');

        transaction.set(voteRef, {vote});
      })
          .then((value) => 'Vote cast')
          .catch((error) => `Failed to cast vote: ${error}`);
    });

exports.getNextBatch = functions
    .region('europe-west1')
    .https
    .onCall(async (data, context) => {
      const {userId, quantity, lastCrossingId} = data;

      functions
          .logger
          .log(
              `Getting next batch of ${quantity} crossings for \
              ${userId}, last crossing id \
              ${lastCrossingId ? lastCrossingId : 'n/a'}`,
          );

      const crossingsCollection = db.collection('crossings');

      let crossingQuery;

      if (lastCrossingId) {
        const lastCrossingFirebaseId = nodeIdToFirestoreId(lastCrossingId);

        const lastCrossingReference = await crossingsCollection
            .doc(lastCrossingFirebaseId)
            .get();

        crossingQuery = crossingsCollection
            .where('unseenBy', 'array-contains', userId)
            .orderBy('votesTotal')
            .startAfter(lastCrossingReference);
      } else {
        crossingQuery = crossingsCollection
            .where('unseenBy', 'array-contains', userId)
            .orderBy('votesTotal');
      }

      const _crossingsQuerySnapshot = await crossingQuery
          .limit(quantity)
          .get();

      return _crossingsQuerySnapshot.docs.map((crossingDocument) =>
        crossingDocument.data());
    });
